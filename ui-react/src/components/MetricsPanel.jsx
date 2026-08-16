import React from "react";
import { Wifi, Info, Shield, Radio, Terminal, Server } from "lucide-react";

export default function MetricsPanel({ wsStatus, state, emotion, voice = "anna", services = {}, onSelectEmotion, onSelectVoice }) {
  const isConnected = wsStatus === "CONNECTED";

  const femaleVoices = [
    { id: "anna", name: "Anna (Default EN)" },
    { id: "cosette", name: "Cosette (Natural)" },
    { id: "eve", name: "Eve (Calm)" },
    { id: "jane", name: "Jane (Clear)" },
    { id: "mary", name: "Mary (Soft)" },
    { id: "vera", name: "Vera (Warm)" },
  ];

  const maleVoices = [
    { id: "alba", name: "Alba (Scottish)" },
    { id: "marius", name: "Marius (Warm)" },
    { id: "jean", name: "Jean (Smooth)" },
    { id: "javert", name: "Javert (Deep)" },
  ];

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-glow"></span>
        <h2>CARIN</h2>
        <span className="version">v2.1</span>
      </div>
      
      <div className="stats-panel">
        <h3>SYSTEM METRICS</h3>
        
        <div className="metric-card">
          <div className="metric-card-header">
            <Wifi size={14} />
            <span className="label">WEB UI SERVER</span>
          </div>
          <span className={`value ${isConnected ? "connected" : "disconnected"}`}>
            {wsStatus}
          </span>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <Server size={14} />
            <span className="label">WSL / LLM BACKEND</span>
          </div>
          <span className={`value ${services.llama_server ? "connected" : "disconnected"}`}>
            {services.llama_server ? "CONNECTED" : "OFFLINE"}
          </span>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <Radio size={14} />
            <span className="label">AGENT STATE</span>
          </div>
          <span className="value">{state}</span>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <Info size={14} />
            <span className="label">CURRENT EMOTION</span>
          </div>
          <span className="value" style={{ textTransform: "uppercase", fontWeight: "bold" }}>{emotion}</span>
        </div>

        {/* Voice Selector Controls */}
        <div className="metric-card" style={{ gridColumn: "span 2" }}>
          <div className="metric-card-header" style={{ marginBottom: "0.4rem", display: "flex", justifyContent: "space-between" }}>
            <span className="label">TTS VOICE ({voice.toUpperCase()})</span>
            <a 
              href="http://localhost:8086" 
              target="_blank" 
              rel="noreferrer"
              style={{ color: "var(--neon-blue)", fontSize: "0.68rem", textDecoration: "underline", cursor: "pointer" }}
            >
              Open Web Tester ↗
            </a>
          </div>
          
          <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>FEMALE VOICES:</div>
          <div className="voice-buttons" style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginBottom: "0.5rem" }}>
            {femaleVoices.map((v) => (
              <button
                key={v.id}
                onClick={() => onSelectVoice && onSelectVoice(v.id)}
                style={{
                  padding: "0.25rem 0.45rem",
                  fontSize: "0.68rem",
                  borderRadius: "4px",
                  border: voice === v.id ? "1px solid var(--neon-blue)" : "1px solid rgba(255,255,255,0.1)",
                  background: voice === v.id ? "rgba(0, 243, 255, 0.25)" : "rgba(10,15,30,0.6)",
                  color: voice === v.id ? "var(--neon-blue)" : "#cbd5e1",
                  cursor: "pointer",
                  fontWeight: voice === v.id ? "bold" : "normal"
                }}
              >
                {v.name}
              </button>
            ))}
          </div>

          <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>MALE VOICES:</div>
          <div className="voice-buttons" style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
            {maleVoices.map((v) => (
              <button
                key={v.id}
                onClick={() => onSelectVoice && onSelectVoice(v.id)}
                style={{
                  padding: "0.25rem 0.45rem",
                  fontSize: "0.68rem",
                  borderRadius: "4px",
                  border: voice === v.id ? "1px solid var(--neon-blue)" : "1px solid rgba(255,255,255,0.1)",
                  background: voice === v.id ? "rgba(0, 243, 255, 0.25)" : "rgba(10,15,30,0.6)",
                  color: voice === v.id ? "var(--neon-blue)" : "#cbd5e1",
                  cursor: "pointer",
                  fontWeight: voice === v.id ? "bold" : "normal"
                }}
              >
                {v.name}
              </button>
            ))}
          </div>
        </div>

        {/* Emotion Override Controls */}
        <div className="metric-card" style={{ gridColumn: "span 2" }}>
          <div className="metric-card-header" style={{ marginBottom: "0.5rem" }}>
            <span className="label">EMOTION OVERRIDE</span>
          </div>
          <div className="emotion-buttons" style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
            {["neutral", "happy", "sad", "surprised", "excited", "angry", "hesitant", "refusing"].map((emo) => (
              <button
                key={emo}
                onClick={() => onSelectEmotion && onSelectEmotion(emo)}
                className={`emotion-btn ${emotion === emo ? "active" : ""}`}
                style={{
                  padding: "0.25rem 0.5rem",
                  fontSize: "0.7rem",
                  borderRadius: "4px",
                  border: emotion === emo ? "1px solid var(--neon-blue)" : "1px solid rgba(255,255,255,0.1)",
                  background: emotion === emo ? "rgba(0, 243, 255, 0.2)" : "rgba(10,15,30,0.6)",
                  color: emotion === emo ? "var(--neon-blue)" : "#a0aec0",
                  cursor: "pointer",
                  transition: "all 0.2s"
                }}
              >
                {emo.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <Shield size={14} />
            <span className="label">ACTIVE MODEL</span>
          </div>
          <span className="value">QWEN 3.5 4B</span>
        </div>
      </div>

      <div className="control-help">
        <h3>ACTIVE SERVICES</h3>
        <div className="service-item">
          <span className={`indicator ${services.mcp_search ? "running" : "stopped"}`}></span>
          <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <Terminal size={12} />
            <span>web-search-mcp (Port 3001)</span>
          </div>
        </div>
        <div className="service-item">
          <span className={`indicator ${services.mcp_time ? "running" : "stopped"}`}></span>
          <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <Terminal size={12} />
            <span>time-mcp (Port 3002)</span>
          </div>
        </div>
        <div className="service-item">
          <span className={`indicator ${services.llama_server ? "running" : "stopped"}`}></span>
          <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <Server size={12} />
            <span>llama-server (Port 8085)</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
