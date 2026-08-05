import React, { useEffect, useState } from "react";

const PATHS = {
  eyes: {
    neutral: {
      left: "M 145 185 Q 160 162 175 185 Q 160 208 145 185",
      right: "M 225 185 Q 240 162 255 185 Q 240 208 225 185",
      fill: "var(--neon-green)"
    },
    happy: {
      left: "M 145 190 Q 160 170 175 190",
      right: "M 225 190 Q 240 170 255 190",
      fill: "none"
    },
    sad: {
      left: "M 145 190 Q 160 175 175 190",
      right: "M 225 190 Q 240 175 255 190",
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
    },
    angry: {
      left: "M 145 180 Q 160 200 175 180",
      right: "M 225 180 Q 240 200 255 180",
      fill: "none"
    },
    hesitant: {
      left: "M 145 180 Q 160 190 175 185",
      right: "M 225 185 Q 240 175 255 185",
      fill: "none"
    },
    refusing: {
      left: "M 145 185 Q 160 170 175 185",
      right: "M 225 185 Q 240 170 255 185",
      fill: "var(--neon-orange)"
    }
  },
  eyebrows: {
    neutral: {
      left: "M 140 148 Q 155 140 170 148",
      right: "M 230 148 Q 245 140 260 148"
    },
    happy: {
      left: "M 140 150 Q 155 142 170 150",
      right: "M 230 150 Q 245 142 260 150"
    },
    sad: {
      left: "M 140 160 Q 155 148 170 145",
      right: "M 230 145 Q 245 148 260 160"
    },
    surprised: {
      left: "M 140 142 Q 155 138 170 142",
      right: "M 230 142 Q 245 138 260 142"
    },
    excited: {
      left: "M 140 145 Q 155 138 170 148",
      right: "M 230 148 Q 245 138 260 145"
    },
    angry: {
      left: "M 140 145 Q 155 158 170 162",
      right: "M 230 162 Q 245 158 260 145"
    },
    hesitant: {
      left: "M 140 145 Q 155 155 170 150",
      right: "M 230 142 Q 245 138 260 145"
    },
    refusing: {
      left: "M 140 145 Q 155 158 170 165",
      right: "M 230 165 Q 245 158 260 145"
    }
  },
  mouth: {
    neutral: "M 170 230 Q 200 258 230 230",
    happy: "M 175 225 Q 200 255 225 225",
    sad: "M 175 255 Q 200 225 225 255",
    surprised: "M 178 235 A 22 28 0 1 0 222 235 A 22 28 0 1 0 178 235",
    excited: "M 170 220 Q 200 265 230 220",
    angry: "M 175 245 Q 200 220 225 245",
    hesitant: "M 175 238 Q 195 248 215 232 Q 225 238 230 240",
    refusing: "M 170 245 H 230",
    thinking: "M 185 235 H 215"
  }
};

export default function RobotFace({ state, emotion, viseme }) {
  const emo = emotion in PATHS.eyes ? emotion : "neutral";
  const [mouthPath, setMouthPath] = useState(PATHS.mouth.neutral);

  // Smooth real-time lip sync morphing based on audio viseme openness frame events
  useEffect(() => {
    if (state === "speaking") {
      const openness = viseme?.openness || 0.1;
      const heightOffset = Math.round(openness * 35); // Dynamic lip open amplitude (0-35px)
      const wideOffset = Math.round(openness * 10);
      
      // Interpolated natural curved viseme mouth shape
      const startX = 175 - wideOffset;
      const endX = 225 + wideOffset;
      const baseY = 230;
      const controlY = baseY + Math.max(5, heightOffset);
      
      setMouthPath(`M ${startX} ${baseY} Q 200 ${controlY} ${endX} ${baseY}`);
    } else if (state === "thinking") {
      setMouthPath(PATHS.mouth.thinking);
    } else {
      setMouthPath(PATHS.mouth[emo] || PATHS.mouth.neutral);
    }
  }, [state, emo, viseme]);

  const eyeStyle = PATHS.eyes[emo];
  const eyebrowStyle = PATHS.eyebrows[emo] || PATHS.eyebrows.neutral;
  const strokeWidth = eyeStyle.fill === "none" ? "8" : "2";

  // Dynamic Neon Color palette per emotion
  const EMOTION_COLORS = {
    neutral: "var(--neon-green)",
    happy: "var(--neon-blue)",
    sad: "#0077ff",
    surprised: "#ff00ea",
    excited: "var(--neon-purple)",
    angry: "var(--neon-red)",
    hesitant: "var(--neon-orange)",
    refusing: "var(--neon-red)"
  };
  const activeColor = EMOTION_COLORS[emo] || "var(--neon-green)";

  // Eye fill logic (uses active color if filled)
  const eyeFillColor = eyeStyle.fill === "none" ? "none" : activeColor;

  // Blush cheek opacity (only shows on happy/excited emotions)
  const blushOpacity = (emo === "happy" || emo === "excited") ? "0.6" : "0";

  return (
    <div className={`face-container emotion-${emo}`} id="face-wrapper">
      <div className="glow-effect" style={{
        background: `radial-gradient(circle, ${activeColor}33, transparent 70%)`
      }}></div>
      
      <svg id="robot-svg" viewBox="0 0 400 400">
        <defs>
          {/* visorglow drop-shadow */}
          <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Pure Neon Glowing Face Features */}
        <g id="neon-face" className={emo === "refusing" ? "gesture-head-shake" : ""}>
          {/* Eyebrows */}
          <path id="left-eyebrow" d={eyebrowStyle.left} stroke={activeColor} strokeWidth="4.5" strokeLinecap="round" fill="none" filter="url(#neon-glow)" style={{ transition: "stroke 0.3s" }} />
          <path id="right-eyebrow" d={eyebrowStyle.right} stroke={activeColor} strokeWidth="4.5" strokeLinecap="round" fill="none" filter="url(#neon-glow)" style={{ transition: "stroke 0.3s" }} />

          {/* Left Eye */}
          <path id="left-eye" d={eyeStyle.left} stroke={activeColor} strokeWidth={strokeWidth} strokeLinecap="round" fill={eyeFillColor} filter="url(#neon-glow)" style={{ transition: "stroke 0.3s, fill 0.3s" }} />
          
          {/* Right Eye */}
          <path id="right-eye" d={eyeStyle.right} stroke={activeColor} strokeWidth={strokeWidth} strokeLinecap="round" fill={eyeFillColor} filter="url(#neon-glow)" style={{ transition: "stroke 0.3s, fill 0.3s" }} />
          
          {/* Blush Cheeks */}
          <circle id="left-blush" cx="135" cy="210" r="10" fill="var(--neon-purple)" opacity={blushOpacity} filter="url(#neon-glow)" style={{ transition: "opacity 0.3s" }} />
          <circle id="right-blush" cx="265" cy="210" r="10" fill="var(--neon-purple)" opacity={blushOpacity} filter="url(#neon-glow)" style={{ transition: "opacity 0.3s" }} />

          {/* Mouth */}
          <path id="mouth" d={mouthPath} stroke={activeColor} strokeWidth="5.5" strokeLinecap="round" fill="none" filter="url(#neon-glow)" style={{ transition: "stroke 0.3s" }} />

          {/* --- GESTURE OVERLAYS --- */}

          {/* 1. Sweat Drop Gesture (for [hesitant] / nervous 😅) */}
          {emo === "hesitant" && (
            <g id="gesture-sweat-drop" filter="url(#neon-glow)" className="sweat-drop-anim">
              <path d="M 285 135 C 285 125, 292 118, 292 118 C 292 118, 299 125, 299 135 C 299 142, 293 147, 285 147 C 278 147, 285 142, 285 135 Z" fill="#00f2fe" opacity="0.95" />
            </g>
          )}

          {/* 2. Refusal Cross Arms / No Hands Gesture (for [refusing] 🙅‍♂️) */}
          {emo === "refusing" && (
            <g id="gesture-refusal-hands" filter="url(#neon-glow)" className="refusal-hands-anim">
              {/* Hand 1 crossing */}
              <path d="M 140 270 L 260 310" stroke="var(--neon-red)" strokeWidth="6" strokeLinecap="round" opacity="0.9" />
              {/* Hand 2 crossing */}
              <path d="M 260 270 L 140 310" stroke="var(--neon-red)" strokeWidth="6" strokeLinecap="round" opacity="0.9" />
            </g>
          )}

          {/* 3. Waving Hand / Sparkles Gesture (for [happy] / [excited] 👋) */}
          {(emo === "happy" || emo === "excited") && (
            <g id="gesture-happy-sparkles" filter="url(#neon-glow)">
              <path d="M 290 120 L 295 130 L 305 135 L 295 140 L 290 150 L 285 140 L 275 135 L 285 130 Z" fill="var(--neon-blue)" opacity="0.8" className="sparkle-anim" />
              <path d="M 100 120 L 105 127 L 115 130 L 105 133 L 100 140 L 95 133 L 85 130 L 95 127 Z" fill="var(--neon-purple)" opacity="0.8" className="sparkle-anim-delayed" />
            </g>
          )}

          {/* 4. Anger Mark Symbol (for [angry] 💢) */}
          {emo === "angry" && (
            <g id="gesture-anger-mark" filter="url(#neon-glow)" className="anger-anim">
              <path d="M 270 125 Q 285 125 285 140 M 285 140 Q 285 155 300 155 M 300 140 Q 285 140 285 125 M 285 155 Q 285 140 270 140" stroke="var(--neon-red)" strokeWidth="4" strokeLinecap="round" fill="none" />
            </g>
          )}
        </g>
      </svg>
    </div>
  );
}
