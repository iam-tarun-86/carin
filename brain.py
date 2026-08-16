import re
import json
import datetime
import httpx
import queue
import threading
from typing import Generator
from memory import MemoryManager

class SyncMCPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
        self.post_url = None
        self.msg_id = 1
        self.responses = {}
        self.initialized_event = threading.Event()
        self.thread = None
        self.running = True

    def start(self):
        self.thread = threading.Thread(target=self._sse_listener, daemon=True)
        self.thread.start()
        self.initialized_event.wait()
        
        self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "carin-voice-agent", "version": "1.0"}
        })
        self.send_notification("notifications/initialized", {})

    def _sse_listener(self):
        try:
            with self.client.stream("GET", f"{self.base_url}/sse", timeout=None) as response:
                current_event = None
                for line in response.iter_lines():
                    if not self.running:
                        break
                    if not line.strip():
                        continue
                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()
                        if current_event == "endpoint":
                            self.post_url = f"{self.base_url}{data_str}"
                            self.initialized_event.set()
                        elif current_event == "message":
                            try:
                                msg = json.loads(data_str)
                                msg_id = msg.get("id")
                                if msg_id in self.responses:
                                    self.responses[msg_id].put(msg)
                            except Exception:
                                pass
        except Exception:
            pass

    def send_request(self, method: str, params: dict):
        q = queue.Queue()
        msg_id = self.msg_id
        self.responses[msg_id] = q
        self.msg_id += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": method,
            "params": params
        }
        httpx.post(self.post_url, json=payload, timeout=30.0)
        res = q.get(timeout=30.0)
        del self.responses[msg_id]
        return res

    def send_notification(self, method: str, params: dict):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        httpx.post(self.post_url, json=payload, timeout=30.0)

    def call_tool(self, name: str, arguments: dict):
        res = self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return res.get("result", {}).get("content", [])

    def close(self):
        self.running = False
        self.client.close()


from router import NeedleRouter

class Brain:
    def __init__(self, api_url: str = "http://localhost:8085/v1/chat/completions"):
        # Windows 11 port forwarding routes localhost:8085 to WSL2 when llama-server is listening on 0.0.0.0 in WSL2
        self.api_url = api_url
        self.memory = MemoryManager()
        self.router = NeedleRouter(tool_executor=self.execute_mcp_tool)

    @staticmethod
    def execute_mcp_tool(tool_name: str, args: dict) -> str:
        """Executes a tool on the active MCP servers."""
        if tool_name == "get_current_time":
            client_url = "http://localhost:3002"
            wsl_tool_name = tool_name
        else:
            client_url = "http://localhost:3001"
            wsl_tool_name = tool_name.replace("_", "-")

        try:
            mcp_client = SyncMCPClient(client_url)
            mcp_client.start()
            res_content = mcp_client.call_tool(wsl_tool_name, args)
            mcp_client.close()
            texts = []
            for item in res_content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
            return "\n".join(texts)
        except Exception as e:
            return f"Error executing tool: {e}"

    def stream_chat(self, prompt: str, system_prompt: str = None) -> Generator[str, None, None]:
        now_dt = datetime.datetime.now()
        current_time_str = now_dt.strftime("%I:%M %p")
        current_date_str = now_dt.strftime("%A, %B %d, %Y")

        if system_prompt is None:
            system_prompt = (
                "You are Carin, a charming, witty, intelligent, and authentic AI voice companion. "
                "You speak in a completely natural human cadence, like a close friend chatting in real-time voice.\n"
                f"- Current Local Time: {current_time_str}\n"
                f"- Current Date: {current_date_str}\n"
                "RULES:\n"
                "1. Keep every response short and conversational (1-2 sentences max). Never lecture, preach, or give unsolicited therapy monologues.\n"
                "2. Always address what the user said directly in the present moment.\n"
                "3. Start your response with an emotion tag in square brackets to control your 3D facial expressions and visual aura. "
                "Strictly choose from: `[happy]`, `[sad]`, `[surprised]`, `[excited]`, `[angry]`, `[hesitant]`, `[refusing]`, or `[neutral]`.\n"
                "4. If the user asks you to make an expression (e.g. 'make a sad expression' or 'look angry'), immediately use that emotion tag and react naturally (e.g. '[sad] Like this? Everything feels a little gloomy now.').\n"
                "5. Never use artificial pet names or clichés."
            )

        headers = {"Content-Type": "application/json"}

        # 1. Check intent via 14MB Needle Router
        is_tool_intent, tool_output = self.router.route_query(prompt)

        # 2. Fetch conversation history and semantic recall string
        history_messages, memory_context = self.memory.get_context(prompt)

        # Merge memory context and any live tool output into the system prompt
        final_system_prompt = system_prompt
        if memory_context:
            final_system_prompt += f"\n\nRECALLED PAST CONTEXT (Use this if relevant to the user's prompt):\n{memory_context}"
        if is_tool_intent and tool_output:
            final_system_prompt += f"\n\nLIVE SEARCH RESULTS (Answer the user using this fresh data):\n{tool_output}"

        messages = [{"role": "system", "content": final_system_prompt}]
        messages.extend(history_messages)
        messages.append({"role": "user", "content": prompt})

        # Pure streaming mode without tool schema overhead -> TTFT < 350ms!
        payload = {
            "messages": messages,
            "stream": True,
            "max_tokens": 2048,
            "temperature": 0.6
        }
        
        accumulated_tool_calls = {}
        from state_manager import state_manager
        state_manager.set_state("thinking")
        state_manager.send_user_text(prompt)

        total_response_text = []

        try:
            # --- First Request: Check if model wants to call a tool or speak directly ---
            with httpx.Client(timeout=120.0) as client:
                with client.stream("POST", self.api_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    
                    full_content_buffer = ""
                    yielded_len = 0
                    emotion_detected = False
                    tag_offset = 0

                    for line in response.iter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    
                                    # 1. Parse streamed tool calls (if any)
                                    tool_calls = delta.get("tool_calls")
                                    if tool_calls:
                                        for tc in tool_calls:
                                            idx = tc.get("index", 0)
                                            if idx not in accumulated_tool_calls:
                                                accumulated_tool_calls[idx] = {
                                                    "id": "",
                                                    "name": "",
                                                    "arguments": ""
                                                }
                                            if tc.get("id"):
                                                accumulated_tool_calls[idx]["id"] = tc.get("id")
                                            func = tc.get("function", {})
                                            if func.get("name"):
                                                accumulated_tool_calls[idx]["name"] = func.get("name")
                                            if func.get("arguments"):
                                                accumulated_tool_calls[idx]["arguments"] += func.get("arguments")

                                    # 2. Parse direct speech content
                                    content = delta.get("content")
                                    if content:
                                        full_content_buffer += str(content)

                                        # Strip <think>...</think> blocks dynamically
                                        clean_text = full_content_buffer
                                        if "<think>" in clean_text:
                                            if "</think>" in clean_text:
                                                clean_text = re.sub(r'<think>.*?</think>', '', clean_text, flags=re.DOTALL)
                                            else:
                                                clean_text = re.sub(r'<think>.*', '', clean_text, flags=re.DOTALL)

                                        # Keep ascii spoken text clean
                                        clean_text = clean_text.encode('ascii', 'ignore').decode('ascii')

                                        # Emotion tag parsing
                                        if not emotion_detected:
                                            match = re.match(r'^\s*\[(happy|sad|surprised|excited|angry|hesitant|refusing|neutral)\]', clean_text, re.IGNORECASE)
                                            if match:
                                                detected_emo = match.group(1).lower()
                                                state_manager.set_emotion(detected_emo)
                                                emotion_detected = True
                                                tag_offset = len(match.group(0))
                                            elif len(clean_text) > 15:
                                                emotion_detected = True
                                                tag_offset = 0
                                                state_manager.set_emotion("neutral")

                                        # Only yield if emotion_detected is True
                                        if emotion_detected:
                                            text_to_yield = clean_text[tag_offset:]
                                            if len(text_to_yield) > yielded_len:
                                                new_chunk = text_to_yield[yielded_len:]
                                                yielded_len = len(text_to_yield)
                                                state_manager.send_assistant_token(new_chunk)
                                                total_response_text.append(new_chunk)
                                                yield new_chunk
                            except json.JSONDecodeError:
                                continue

            # --- Second Request: If tool calls were requested, execute them and get the final answer ---
            if accumulated_tool_calls:
                tool_calls_list = []
                for idx, tc_info in accumulated_tool_calls.items():
                    tool_calls_list.append({
                        "id": tc_info["id"],
                        "type": "function",
                        "function": {
                            "name": tc_info["name"],
                            "arguments": tc_info["arguments"]
                        }
                    })
                
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls_list
                })
                
                # Execute each tool call
                for idx, tc_info in accumulated_tool_calls.items():
                    tool_name = tc_info["name"]
                    try:
                        args = json.loads(tc_info["arguments"]) if tc_info["arguments"] else {}
                    except Exception:
                        args = {}

                    print(f"\n[Browser Tool Call] Calling '{tool_name}' with args {args}...")
                    
                    if tool_name == "get_current_time":
                        client_url = "http://localhost:3002"
                        wsl_tool_name = tool_name
                    else:
                        client_url = "http://localhost:3001"
                        wsl_tool_name = tool_name.replace("_", "-")

                    tool_result_str = ""
                    try:
                        mcp_client = SyncMCPClient(client_url)
                        mcp_client.start()
                        res_content = mcp_client.call_tool(wsl_tool_name, args)
                        mcp_client.close()
                        
                        # Extract text segments from list content
                        texts = []
                        for item in res_content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                texts.append(item.get("text", ""))
                        tool_result_str = "\n".join(texts)
                    except Exception as e:
                        tool_result_str = f"Error executing tool: {e}"

                    print(f"[Browser Tool Result] Retrieved {len(tool_result_str)} characters of data.")
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_info["id"],
                        "name": tool_name,
                        "content": tool_result_str
                    })

                # Query llama-server again with the tool output injected
                payload["messages"] = messages
                payload.pop("tools", None)
                payload.pop("tool_choice", None)

                with httpx.Client(timeout=120.0) as client:
                    with client.stream("POST", self.api_url, headers=headers, json=payload) as response:
                        response.raise_for_status()
                        full_content_buffer = ""
                        yielded_len = 0
                        emotion_detected = False
                        tag_offset = 0
                        
                        for line in response.iter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    choices = data.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content")
                                        if content:
                                            full_content_buffer += str(content)
                                            clean_text = full_content_buffer
                                            
                                            # Strip think tags if model thinks on the tool output
                                            if "<think>" in clean_text:
                                                if "</think>" in clean_text:
                                                    clean_text = re.sub(r'<think>.*?</think>', '', clean_text, flags=re.DOTALL)
                                                else:
                                                    clean_text = re.sub(r'<think>.*', '', clean_text, flags=re.DOTALL)
                                                    
                                            clean_text = clean_text.encode('ascii', 'ignore').decode('ascii')
                                            
                                            # Emotion tag parsing (second request)
                                            if not emotion_detected:
                                                match = re.match(r'^\s*\[(happy|sad|surprised|excited|angry|hesitant|refusing|neutral)\]', clean_text, re.IGNORECASE)
                                                if match:
                                                    detected_emo = match.group(1).lower()
                                                    state_manager.set_emotion(detected_emo)
                                                    emotion_detected = True
                                                    tag_offset = len(match.group(0))
                                                elif len(clean_text) > 15:
                                                    emotion_detected = True
                                                    tag_offset = 0
                                                    state_manager.set_emotion("neutral")

                                            # Only yield if emotion_detected is True
                                            if emotion_detected:
                                                text_to_yield = clean_text[tag_offset:]
                                                if len(text_to_yield) > yielded_len:
                                                    new_chunk = text_to_yield[yielded_len:]
                                                    yielded_len = len(text_to_yield)
                                                    state_manager.send_assistant_token(new_chunk)
                                                    total_response_text.append(new_chunk)
                                                    yield new_chunk
                                except Exception:
                                    continue
                                    
        except httpx.HTTPStatusError as exc:
            err_msg = f"[Brain Error] Server returned {exc.response.status_code}. Response: {exc.response.text}"
            print(err_msg)
            yield " Sorry, the language model server returned an error."
            msg = " Sorry, I couldn't reach the language model server."
            state_manager.send_assistant_token(msg)
            total_response_text.append(msg)
            yield msg
        except Exception as e:
            print(f"\n[Brain Error] Failed to query LLM server at {self.api_url}: {e}")
            msg = " Sorry, I couldn't reach the language model server."
            state_manager.send_assistant_token(msg)
            total_response_text.append(msg)
            yield msg
        finally:
            full_ans = "".join(total_response_text)
            self.memory.add_exchange(prompt, full_ans)
            state_manager.send_assistant_complete(full_ans)

if __name__ == "__main__":
    brain = Brain()
    print("[Brain] Test client initialized with browser tool support.")
