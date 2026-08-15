import asyncio
import json
import threading
import websockets

class StateManager:
    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.state = "idle"
        self.emotion = "neutral"
        
        self.loop = None
        self.server_thread = None

    def start(self):
        """Starts the WebSocket server in a daemon background thread."""
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

    def _run_server(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.loop.run_until_complete(self._start_server_async())
        self.loop.run_forever()

    async def _start_server_async(self):
        await websockets.serve(self._handler, self.host, self.port)
        print(f"[StateManager] WebSocket Server running on ws://{self.host}:{self.port}")
        asyncio.create_task(self._check_services_periodically())

    async def _check_services_periodically(self):
        import httpx
        while True:
            services = {
                "mcp_search": False,
                "mcp_time": False,
                "llama_server": False
            }
            async with httpx.AsyncClient(timeout=1.0) as client:
                # Check web search mcp
                try:
                    r = await client.get("http://127.0.0.1:3001/sse")
                    services["mcp_search"] = True
                except Exception:
                    pass

                # Check time mcp
                try:
                    r = await client.get("http://127.0.0.1:3002/sse")
                    services["mcp_time"] = True
                except Exception:
                    pass

                # Check llama-server
                try:
                    r = await client.get("http://127.0.0.1:8085/v1/models")
                    services["llama_server"] = r.status_code == 200
                except Exception:
                    pass

            self._broadcast({
                "type": "services_status",
                "services": services
            })
            await asyncio.sleep(3)

    async def _handler(self, websocket):
        self.clients.add(websocket)
        # Send current state upon connection
        await websocket.send(json.dumps({
            "type": "status",
            "state": self.state,
            "emotion": self.emotion
        }))
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    if msg_type == "set_emotion":
                        self.set_emotion(data.get("emotion", "neutral"))
                    elif msg_type == "set_state":
                        self.set_state(data.get("state", "idle"))
                except Exception:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)

    def _broadcast(self, data):
        """Broadcast helper to send data to all connected clients."""
        if not self.loop or not self.clients:
            return
        payload = json.dumps(data)
        asyncio.run_coroutine_threadsafe(
            self._send_to_all(payload), 
            self.loop
        )

    async def _send_to_all(self, payload):
        if self.clients:
            await asyncio.gather(
                *[client.send(payload) for client in self.clients], 
                return_exceptions=True
            )

    # Thread-safe setters
    def set_state(self, state):
        if state != self.state:
            self.state = state
            self._broadcast({
                "type": "status",
                "state": self.state,
                "emotion": self.emotion
            })

    def set_emotion(self, emotion):
        if emotion != self.emotion:
            self.emotion = emotion
            self._broadcast({
                "type": "status",
                "state": self.state,
                "emotion": self.emotion
            })

    def set_state_and_emotion(self, state, emotion):
        self.state = state
        self.emotion = emotion
        self._broadcast({
            "type": "status",
            "state": self.state,
            "emotion": self.emotion
        })

    def send_user_text(self, text):
        self._broadcast({
            "type": "user_text",
            "text": text
        })

    def send_assistant_token(self, token):
        self._broadcast({
            "type": "assistant_token",
            "token": token
        })

    def send_assistant_complete(self, text):
        self._broadcast({
            "type": "assistant_complete",
            "text": text
        })

    def send_audio_amplitude(self, amplitude):
        self._broadcast({
            "type": "audio_amplitude",
            "amplitude": round(float(amplitude), 4)
        })

    def send_viseme(self, loudness, mouth_openness):
        self._broadcast({
            "type": "viseme",
            "loudness": round(float(loudness), 3),
            "openness": round(float(mouth_openness), 3)
        })

# Global singleton
state_manager = StateManager()
