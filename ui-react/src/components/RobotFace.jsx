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
    }
  },
  mouth: {
    neutral: "M 170 230 Q 200 258 230 230",
    happy: "M 175 225 Q 200 255 225 225",
    sad: "M 175 255 Q 200 225 225 255",
    surprised: "M 178 235 A 22 28 0 1 0 222 235 A 22 28 0 1 0 178 235",
    excited: "M 170 220 Q 200 265 230 220",
    angry: "M 175 245 Q 200 220 225 245",
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
    angry: "var(--neon-red)"
  };
  const activeColor = EMOTION_COLORS[emo] || "var(--neon-green)";

  // Eye fill logic (uses active color if filled)
  const eyeFillColor = eyeStyle.fill === "none" ? "none" : activeColor;

  // Blush cheek opacity (only shows on happy/excited emotions)
  const blushOpacity = (emo === "happy" || emo === "excited") ? "0.6" : "0";

  return (
    <div className="face-container" id="face-wrapper">
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
        <g id="neon-face">
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
        </g>
      </svg>
    </div>
  );
}
