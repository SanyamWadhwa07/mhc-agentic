"use client";

import { motion, AnimatePresence } from "framer-motion";

export type AvatarState = "idle" | "thinking" | "speaking";

interface AvatarProps {
  state?: AvatarState;
  size?: number;
}

const ORBIT_DOTS = [0, 120, 240]; // degrees apart

export default function Avatar({ state = "idle", size = 64 }: AvatarProps) {
  const isThinking = state === "thinking";
  const isSpeaking = state === "speaking";

  return (
    <div
      style={{ width: size, height: size }}
      className="relative flex items-center justify-center select-none"
    >
      {/* Outer glow ring — pulses when speaking */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(99,102,241,0.25) 0%, transparent 70%)",
        }}
        animate={
          isSpeaking
            ? { scale: [1, 1.18, 1], opacity: [0.6, 1, 0.6] }
            : { scale: 1, opacity: 0.4 }
        }
        transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Orbiting dots when thinking */}
      <AnimatePresence>
        {isThinking &&
          ORBIT_DOTS.map((deg, i) => (
            <motion.div
              key={i}
              className="absolute rounded-full bg-mahi-400"
              style={{
                width: size * 0.1,
                height: size * 0.1,
                top: "50%",
                left: "50%",
                marginTop: -(size * 0.05),
                marginLeft: -(size * 0.05),
              }}
              initial={{ opacity: 0 }}
              animate={{
                opacity: 1,
                rotate: [deg, deg + 360],
                x: Math.cos((deg * Math.PI) / 180) * (size * 0.52),
                y: Math.sin((deg * Math.PI) / 180) * (size * 0.52),
              }}
              exit={{ opacity: 0 }}
              transition={{
                rotate: { duration: 1.2, repeat: Infinity, ease: "linear", delay: i * 0 },
                opacity: { duration: 0.3 },
              }}
            />
          ))}
      </AnimatePresence>

      {/* Main face — floats when idle */}
      <motion.svg
        width={size * 0.82}
        height={size * 0.82}
        viewBox="0 0 80 80"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        animate={
          isThinking
            ? { y: 0, scale: 0.92 }
            : isSpeaking
            ? { scale: [1, 1.04, 1], y: 0 }
            : { y: [0, -4, 0] }
        }
        transition={
          isThinking
            ? { duration: 0.2 }
            : isSpeaking
            ? { duration: 0.7, repeat: Infinity, ease: "easeInOut" }
            : { duration: 3, repeat: Infinity, ease: "easeInOut" }
        }
      >
        {/* Face gradient */}
        <defs>
          <radialGradient id="faceGrad" cx="50%" cy="45%" r="55%">
            <stop offset="0%" stopColor="#7c6ff7" />
            <stop offset="100%" stopColor="#4338ca" />
          </radialGradient>
          <radialGradient id="blushGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#f9a8d4" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#f9a8d4" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Head */}
        <circle cx="40" cy="40" r="36" fill="url(#faceGrad)" />

        {/* Shine highlight */}
        <ellipse cx="30" cy="24" rx="8" ry="5" fill="white" fillOpacity="0.18" />

        {/* Blush left */}
        <ellipse cx="20" cy="50" rx="8" ry="5" fill="url(#blushGrad)" />
        {/* Blush right */}
        <ellipse cx="60" cy="50" rx="8" ry="5" fill="url(#blushGrad)" />

        {/* Left eye */}
        <motion.g
          animate={{ scaleY: [1, 1, 0.08, 1, 1] }}
          transition={{ duration: 4, repeat: Infinity, repeatDelay: 2.5, ease: "easeInOut" }}
          style={{ transformOrigin: "28px 38px" }}
        >
          <ellipse cx="28" cy="38" rx="5" ry="6" fill="white" />
          <circle cx="29" cy="39" r="3" fill="#1e1b4b" />
          <circle cx="30" cy="37" r="1.2" fill="white" />
        </motion.g>

        {/* Right eye */}
        <motion.g
          animate={{ scaleY: [1, 1, 0.08, 1, 1] }}
          transition={{ duration: 4, repeat: Infinity, repeatDelay: 2.5, ease: "easeInOut" }}
          style={{ transformOrigin: "52px 38px" }}
        >
          <ellipse cx="52" cy="38" rx="5" ry="6" fill="white" />
          <circle cx="53" cy="39" r="3" fill="#1e1b4b" />
          <circle cx="54" cy="37" r="1.2" fill="white" />
        </motion.g>

        {/* Thinking eyes — half closed dots */}
        {isThinking && (
          <>
            <ellipse cx="28" cy="40" rx="5" ry="2.5" fill="#1e1b4b" />
            <ellipse cx="52" cy="40" rx="5" ry="2.5" fill="#1e1b4b" />
          </>
        )}

        {/* Mouth — small curve, wiggles when speaking */}
        <motion.path
          d={isSpeaking ? "M 30 54 Q 40 62 50 54" : "M 32 54 Q 40 60 48 54"}
          stroke="white"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
          animate={
            isSpeaking
              ? { d: ["M 30 54 Q 40 62 50 54", "M 30 56 Q 40 58 50 56", "M 30 54 Q 40 62 50 54"] }
              : {}
          }
          transition={{ duration: 0.5, repeat: isSpeaking ? Infinity : 0 }}
        />

        {/* Small heart above head when idle */}
        <AnimatePresence>
          {state === "idle" && (
            <motion.text
              x="50"
              y="10"
              fontSize="10"
              textAnchor="middle"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: [0, 1, 1, 0], y: [14, 8, 8, 2] }}
              exit={{ opacity: 0 }}
              transition={{ duration: 3.5, repeat: Infinity, repeatDelay: 3 }}
            >
              💙
            </motion.text>
          )}
        </AnimatePresence>
      </motion.svg>
    </div>
  );
}
