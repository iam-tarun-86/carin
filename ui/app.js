const WS_URL = "ws://127.0.0.1:8765";

// DOM Elements
const wsStatus = document.getElementById("ws-status");
const agentState = document.getElementById("agent-state");
const agentEmotion = document.getElementById("agent-emotion");
const statusDisplay = document.getElementById("status-display");
const transcriptContainer = document.getElementById("transcript-container");
const faceWrapper = document.getElementById("face-wrapper");

const leftEye = document.getElementById("left-eye");
const rightEye = document.getElementById("right-eye");
const leftEyebrow = document.getElementById("left-eyebrow");
const rightEyebrow = document.getElementById("right-eyebrow");
const leftBlush = document.getElementById("left-blush");
const rightBlush = document.getElementById("right-blush");
const mouth = document.getElementById("mouth");

// State & Emotion Configuration
let currentEmotion = "neutral";
let currentState = "idle";
let speakingInterval = null;

// SVG Path definitions for morphing animations
const PATHS = {
  eyes: {
    neutral: {
      left: "M 145 185 Q 160 165 175 185 Q 160 205 145 185",
      right: "M 225 185 Q 240 165 255 185 Q 240 205 225 185",
      fill: "var(--neon-blue)"
    },
    happy: {
      left: "M 145 190 Q 160 170 175 190",
      right: "M 225 190 Q 240 170 255 190",
      fill: "none"
    },
    sad: {
      left: "M 145 180 Q 160 200 175 180",
      right: "M 225 180 Q 240 200 255 180",
      fill: "none"
    },
    surprised: {
      left: "M 143 185 Q 160 155 178 185 Q 160 215 142 185",
      right: "M 223 185 Q 240 155 257 185 Q 240 215 223 185",
      fill: "var(--neon-blue)"
    },
    excited: {
      left: "M 145 190 Q 160 165 175 190",
      right: "M 225 190 Q 240 165 255 190",
      fill: "none"
    }
  },
  eyebrows: {
    neutral: {
      left: "M 140 155 Q 155 155 170 155",
      right: "M 230 155 Q 245 155 260 155"
    },
    happy: {
      left: "M 140 150 Q 155 142 170 150",
      right: "M 230 150 Q 245 142 260 150"
    },
    sad: {
      left: "M 140 150 Q 155 160 170 162",
      right: "M 230 162 Q 245 160 260 150"
    },
    surprised: {
      left: "M 140 142 Q 155 138 170 142",
      right: "M 230 142 Q 245 138 260 142"
    },
    excited: {
      left: "M 140 145 Q 155 138 170 148",
      right: "M 230 148 Q 245 138 260 145"
    }
  },
  mouth: {
    neutral: "M 175 235 Q 200 235 225 235",
    happy: "M 175 225 Q 200 260 225 225",
    sad: "M 175 250 Q 200 220 225 250",
    surprised: "M 190 235 Q 200 215 210 235 Q 200 255 190 235",
    excited: "M 170 220 Q 200 265 230 220",
    thinking: "M 185 235 H 215"
  }
};

// Connect to WebSocket Server
function connect() {
  wsStatus.textContent = "CONNECTING...";
  wsStatus.className = "value disconnected";
  
  const socket = new WebSocket(WS_URL);
  
  socket.onopen = () => {
    wsStatus.textContent = "CONNECTED";
    wsStatus.className = "value connected";
    console.log("[WebSocket] Connected successfully!");
  };
  
  socket.onmessage = (event) => {
    try {
      const data = jsonParse(event.data);
      if (!data) return;
      
      switch (data.type) {
        case "status":
          handleStatusUpdate(data.state, data.emotion);
          break;
        case "user_text":
          addUserMessage(data.text);
          break;
        case "assistant_token":
          appendAssistantToken(data.token);
          break;
        case "assistant_complete":
          finalizeAssistantMessage(data.text);
          break;
      }
    } catch (err) {
      console.error("[WebSocket] Message error:", err);
    }
  };
  
  socket.onclose = () => {
    wsStatus.textContent = "DISCONNECTED";
    wsStatus.className = "value disconnected";
    console.log("[WebSocket] Disconnected. Reconnecting in 3 seconds...");
    setTimeout(connect, 3000);
  };

  socket.onerror = (err) => {
    console.error("[WebSocket] Connection error:", err);
    socket.close();
  };
}

function jsonParse(str) {
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}

// Handle real-time updates for State & Emotion
function handleStatusUpdate(state, emotion) {
  currentState = state;
  currentEmotion = emotion;

  // Update UI Panels
  agentState.textContent = state;
  agentEmotion.textContent = emotion;
  statusDisplay.textContent = state.toUpperCase();

  // Reset page theme classes
  document.body.className = `state-${state}`;

  // Reset active speaking intervals
  if (speakingInterval) {
    clearInterval(speakingInterval);
    speakingInterval = null;
  }

  // Update Face shapes
  updateFaceExpression();

  // If speaking, start talk animation
  if (state === "speaking") {
    startSpeakingAnimation();
  }
}

function updateFaceExpression() {
  const emo = currentEmotion in PATHS.eyes ? currentEmotion : "neutral";
  
  // Set Eye shape & properties
  leftEye.setAttribute("d", PATHS.eyes[emo].left);
  rightEye.setAttribute("d", PATHS.eyes[emo].right);
  leftEye.setAttribute("fill", PATHS.eyes[emo].fill);
  rightEye.setAttribute("fill", PATHS.eyes[emo].fill);

  // Set default stroke widths based on design
  const strokeWidth = PATHS.eyes[emo].fill === "none" ? "8" : "2";
  leftEye.setAttribute("stroke-width", strokeWidth);
  rightEye.setAttribute("stroke-width", strokeWidth);

  // Set Eyebrow shape
  const brow = emo in PATHS.eyebrows ? emo : "neutral";
  leftEyebrow.setAttribute("d", PATHS.eyebrows[brow].left);
  rightEyebrow.setAttribute("d", PATHS.eyebrows[brow].right);

  // Set Blush Cheeks opacity (show if happy or excited)
  const blushOpacity = (emo === "happy" || emo === "excited") ? "0.6" : "0";
  leftBlush.style.opacity = blushOpacity;
  rightBlush.style.opacity = blushOpacity;

  // Set Mouth shape
  if (currentState === "thinking") {
    mouth.setAttribute("d", PATHS.mouth.thinking);
  } else {
    const mouthPath = PATHS.mouth[emo] || PATHS.mouth.neutral;
    mouth.setAttribute("d", mouthPath);
  }
}

// Animates the mouth path height back and forth to simulate speaking
function startSpeakingAnimation() {
  let frame = 0;
  const talkingMouthPaths = [
    "M 175 230 Q 200 255 225 230", // Happy open
    "M 175 238 Q 200 242 225 238", // Flat talking
    "M 175 225 Q 200 260 225 225", // Wide open
    "M 185 235 Q 200 250 215 235"  // Rounded speaking
  ];
  
  speakingInterval = setInterval(() => {
    const path = talkingMouthPaths[frame % talkingMouthPaths.length];
    mouth.setAttribute("d", path);
    frame++;
  }, 120);
}

// Append Chat Messages
function addUserMessage(text) {
  removePlaceholder();
  
  const msg = document.createElement("div");
  msg.className = "message-bubble user";
  msg.innerHTML = `<span class="speaker-tag">You</span>${escapeHTML(text)}`;
  
  transcriptContainer.appendChild(msg);
  scrollToBottom();
}

let currentAssistantBubble = null;

function appendAssistantToken(token) {
  removePlaceholder();
  
  if (!currentAssistantBubble) {
    currentAssistantBubble = document.createElement("div");
    currentAssistantBubble.className = "message-bubble assistant streaming";
    currentAssistantBubble.innerHTML = `<span class="speaker-tag">Carin</span><span class="text-content"></span>`;
    transcriptContainer.appendChild(currentAssistantBubble);
  }
  
  const textContainer = currentAssistantBubble.querySelector(".text-content");
  textContainer.textContent += token;
  scrollToBottom();
}

function finalizeAssistantMessage(fullText) {
  if (currentAssistantBubble) {
    currentAssistantBubble.classList.remove("streaming");
    const textContainer = currentAssistantBubble.querySelector(".text-content");
    textContainer.textContent = fullText;
    currentAssistantBubble = null;
  }
  scrollToBottom();
}

function removePlaceholder() {
  const placeholder = transcriptContainer.querySelector(".chat-placeholder");
  if (placeholder) {
    placeholder.remove();
  }
}

function scrollToBottom() {
  transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
}

function escapeHTML(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}

// Start WebSocket connection
connect();
