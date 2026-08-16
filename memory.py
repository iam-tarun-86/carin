import os
import sqlite3
import datetime
import uuid
import chromadb

class MemoryManager:
    def __init__(self, db_path="memory.db", chroma_path="chroma_db"):
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.session_id = str(uuid.uuid4())[:8]
        
        print(f"[Memory] Initializing SQLite Short-Term Memory (Session: {self.session_id})...")
        self._init_sqlite()
        
        print("[Memory] Initializing ChromaDB Long-Term Memory...")
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.chroma_client.get_or_create_collection(name="carin_memories")
        print("[Memory] Memory Subsystem Ready.")

    def _init_sqlite(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      session_id TEXT,
                      timestamp TEXT,
                      role TEXT,
                      content TEXT)''')
        conn.commit()
        conn.close()

    def add_exchange(self, user_text: str, assistant_text: str):
        """Saves a complete conversation turn to both short-term (session) and long-term memory."""
        if not user_text.strip() or not assistant_text.strip():
            return
            
        timestamp = datetime.datetime.now().isoformat()
        
        # 1. Save to SQLite (Current Session)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO history (session_id, timestamp, role, content) VALUES (?, ?, ?, ?)", 
                  (self.session_id, timestamp, "user", user_text))
        c.execute("INSERT INTO history (session_id, timestamp, role, content) VALUES (?, ?, ?, ?)", 
                  (self.session_id, timestamp, "assistant", assistant_text))
        conn.commit()
        conn.close()
        
        # 2. Save to ChromaDB (Long-Term Semantic Memory)
        doc_id = f"exchange_{timestamp}_{uuid.uuid4().hex[:6]}"
        combined_text = f"User: {user_text} | Assistant: {assistant_text}"
        
        try:
            self.collection.add(
                documents=[combined_text],
                metadatas=[{"timestamp": timestamp, "session_id": self.session_id}],
                ids=[doc_id]
            )
        except Exception as e:
            print(f"[Memory Error] Failed to add to ChromaDB: {e}")

    def get_context(self, current_prompt: str, short_term_limit=6, long_term_limit=2) -> tuple:
        """
        Retrieves recent conversation history from the current active session (short-term)
        and truly relevant past facts/context (long-term).
        """
        context_messages = []
        
        # 1. Fetch Long-Term Memories ONLY for substantive queries (ignore greetings)
        recalled_memories = []
        clean_p = current_prompt.strip().lower()
        is_trivial_greeting = any(clean_p.startswith(g) for g in ["hi", "hello", "hey", "good morning", "good evening", "how are you", "who are you", "what's your name", "what is your name"])
        
        if not is_trivial_greeting and len(clean_p.split()) >= 3:
            try:
                results = self.collection.query(
                    query_texts=[current_prompt],
                    n_results=long_term_limit,
                    include=["documents", "distances"]
                )
                if results and results.get('documents') and results['documents'][0]:
                    docs = results['documents'][0]
                    distances = results.get('distances', [[]])[0]
                    # Only accept high-similarity memories (distance <= 0.85)
                    for doc, dist in zip(docs, distances):
                        if dist <= 0.85:
                            recalled_memories.append(doc)
            except Exception as e:
                print(f"[Memory Warning] ChromaDB query failed: {e}")

        memory_str = ""
        if recalled_memories:
            memory_str = "\n".join(f"- {m}" for m in recalled_memories)

        # 2. Fetch Short-Term History ONLY for the CURRENT active session
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT role, content FROM history WHERE session_id = ? ORDER BY id DESC LIMIT ?", 
                  (self.session_id, short_term_limit))
        rows = c.fetchall()
        conn.close()
        
        # Reverse to chronological order
        for role, content in reversed(rows):
            context_messages.append({"role": role, "content": content})
            
        return context_messages, memory_str
