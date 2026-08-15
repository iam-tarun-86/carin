import os
import sqlite3
import datetime
import chromadb

class MemoryManager:
    def __init__(self, db_path="memory.db", chroma_path="chroma_db"):
        self.db_path = db_path
        self.chroma_path = chroma_path
        
        print("[Memory] Initializing SQLite Short-Term Memory...")
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
                      timestamp TEXT,
                      role TEXT,
                      content TEXT)''')
        conn.commit()
        conn.close()

    def add_exchange(self, user_text: str, assistant_text: str):
        """Saves a complete conversation turn to both short-term and long-term memory."""
        timestamp = datetime.datetime.now().isoformat()
        
        # 1. Save to SQLite (Short-Term)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO history (timestamp, role, content) VALUES (?, ?, ?)", (timestamp, "user", user_text))
        c.execute("INSERT INTO history (timestamp, role, content) VALUES (?, ?, ?)", (timestamp, "assistant", assistant_text))
        conn.commit()
        
        # 2. Save to ChromaDB (Long-Term)
        # We store the exchange as a single combined document so it can be retrieved as full context
        doc_id = f"exchange_{timestamp}"
        combined_text = f"User: {user_text}\nAssistant: {assistant_text}"
        
        try:
            self.collection.add(
                documents=[combined_text],
                metadatas=[{"timestamp": timestamp}],
                ids=[doc_id]
            )
        except Exception as e:
            print(f"[Memory Error] Failed to add to ChromaDB: {e}")
            
        conn.close()

    def get_context(self, current_prompt: str, short_term_limit=6, long_term_limit=2) -> list:
        """
        Retrieves recent conversation history (short-term) and relevant past memories (long-term).
        Returns a list of message dicts formatted for the LLM.
        """
        context_messages = []
        
        # 1. Fetch Long-Term Memories via Semantic Search
        recalled_memories = []
        try:
            results = self.collection.query(
                query_texts=[current_prompt],
                n_results=long_term_limit
            )
            if results and results['documents'] and results['documents'][0]:
                recalled_memories = results['documents'][0]
        except Exception as e:
            print(f"[Memory Warning] ChromaDB query failed: {e}")

        # Inject recalled memories as a system context block if they exist
        if recalled_memories:
            memory_str = "\n---\n".join(recalled_memories)
            context_messages.append({
                "role": "system", 
                "content": f"RECALLED PAST CONTEXT (Use this if relevant to the user's prompt):\n{memory_str}"
            })

        # 2. Fetch Short-Term History (Sliding Window)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT role, content FROM history ORDER BY id DESC LIMIT ?", (short_term_limit,))
        rows = c.fetchall()
        conn.close()
        
        # Reverse because we fetched DESC but LLM needs chronological order
        for role, content in reversed(rows):
            context_messages.append({"role": role, "content": content})
            
        return context_messages
