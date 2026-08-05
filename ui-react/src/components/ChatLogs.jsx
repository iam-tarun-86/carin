import React, { useEffect, useRef } from "react";

export default function ChatLogs({ messages }) {
  const containerRef = useRef(null);

  // Auto-scroll to bottom whenever messages update
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <section className="transcript-section">
      <div className="transcript-box" ref={containerRef}>
        {messages.length === 0 ? (
          <div className="chat-placeholder">
            Start speaking to begin the conversation...
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`message-bubble ${msg.sender} ${
                msg.streaming ? "streaming" : ""
              }`}
            >
              <span className="speaker-tag">
                {msg.sender === "user" ? "You" : "Carin"}
              </span>
              <span className="text-content">{msg.text}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
