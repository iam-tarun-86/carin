import React, { useEffect, useState, useRef } from "react";
import HologramFace from "./components/HologramFace";
import MetricsPanel from "./components/MetricsPanel";
import ChatLogs from "./components/ChatLogs";
import "./App.css";

const WS_URL = "ws://127.0.0.1:8765";

export default function App() {
  const [wsStatus, setWsStatus] = useState("CONNECTING...");
  const [state, setState] = useState("idle");
  const [emotion, setEmotion] = useState("neutral");
  const [messages, setMessages] = useState([]);
  const [amplitude, setAmplitude] = useState(0);

  const [viseme, setViseme] = useState({ loudness: 0, openness: 0 });
  const [services, setServices] = useState({
    mcp_search: false,
    mcp_time: false,
    llama_server: false
  });

  // Use a ref for messages to access the fresh state in WebSocket callbacks
  const messagesRef = useRef(messages);
  const socketRef = useRef(null);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const sendEmotion = (newEmotion) => {
    setEmotion(newEmotion);
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "set_emotion", emotion: newEmotion }));
    }
  };

  useEffect(() => {
    let socket;
    let reconnectTimeout;

    function connect() {
      setWsStatus("CONNECTING...");
      socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        setWsStatus("CONNECTED");
        socketRef.current = socket;
        console.log("[WebSocket] Connected successfully!");
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (!data) return;

          switch (data.type) {
            case "status":
              setState(data.state);
              setEmotion(data.emotion);
              document.body.className = `state-${data.state}`;
              break;

            case "viseme":
              setViseme({ loudness: data.loudness, openness: data.openness });
              break;

            case "audio_amplitude":
              setAmplitude(data.amplitude);
              break;

            case "services_status":
              setServices(data.services);
              break;

            case "user_text":
              setMessages((prev) => [
                ...prev,
                { sender: "user", text: data.text, streaming: false },
              ]);
              break;

            case "assistant_token":
              setMessages((prev) => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg && lastMsg.sender === "assistant" && lastMsg.streaming) {
                  lastMsg.text += data.token;
                  return updated;
                } else {
                  return [
                    ...prev,
                    { sender: "assistant", text: data.token, streaming: true },
                  ];
                }
              });
              break;

            case "assistant_complete":
              setMessages((prev) => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg && lastMsg.sender === "assistant") {
                  lastMsg.text = data.text;
                  lastMsg.streaming = false;
                }
                return updated;
              });
              break;
          }
        } catch (err) {
          console.error("[WebSocket] Message parsing error:", err);
        }
      };

      socket.onclose = () => {
        setWsStatus("DISCONNECTED");
        console.log("[WebSocket] Connection closed. Reconnecting in 3s...");
        reconnectTimeout = setTimeout(connect, 3000);
      };

      socket.onerror = (err) => {
        console.error("[WebSocket] Connection error:", err);
        socket.close();
      };
    }

    connect();

    return () => {
      if (socket) socket.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  return (
    <div className="app-container">
      <div className="glass-bg"></div>
      
      {/* Sidebar Control Panel */}
      <MetricsPanel wsStatus={wsStatus} state={state} emotion={emotion} services={services} onSelectEmotion={sendEmotion} />

      {/* Main Content Area */}
      <main className="main-content">
        
        {/* Hologram Face Visualization */}
        <section className="visualizer-section" style={{ position: 'relative', width: '100%', height: '400px', overflow: 'hidden', borderRadius: '15px' }}>
          <HologramFace emotion={emotion} amplitude={amplitude} />
          <div className="state-indicator-text" style={{ position: 'absolute', bottom: '10px', right: '10px', zIndex: 10 }}>{state.toUpperCase()}</div>
        </section>

        {/* Conversation log section */}
        <ChatLogs messages={messages} />

      </main>
    </div>
  );
}
