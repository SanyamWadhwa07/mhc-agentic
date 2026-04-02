"use client";

import { useId } from "react";
import { motion, AnimatePresence } from "framer-motion";

export type AvatarState = "idle" | "thinking" | "speaking";

interface AvatarProps {
  state?: AvatarState;
  size?: number;
}

export default function Avatar({ state = "idle", size = 56 }: AvatarProps) {
  const uid = useId().replace(/:/g, "");
  const isThinking = state === "thinking";
  const isSpeaking = state === "speaking";
  const dotSize    = size * 0.11;
  const orbitR     = size * 0.52;

  return (
    <div style={{ width: size, height: size }} className="relative flex items-center justify-center flex-shrink-0 select-none">

      {/* Speaking glow */}
      <AnimatePresence>
        {isSpeaking && (
          <motion.div
            key="glow"
            className="absolute inset-0 rounded-full"
            style={{ background: "radial-gradient(circle, rgba(124,106,245,0.35) 0%, transparent 68%)" }}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: [1, 1.25, 1], opacity: [0.5, 1, 0.5] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
      </AnimatePresence>

      {/* Thinking orbiting dots */}
      <AnimatePresence>
        {isThinking && [0, 1, 2].map(i => (
          <motion.div
            key={i}
            style={{ position: "absolute", width: 0, height: 0, top: "50%", left: "50%" }}
            animate={{ rotate: [i * 120, i * 120 + 360] }}
            transition={{ duration: 1.3, repeat: Infinity, ease: "linear", delay: i * 0.08 }}
          >
            <motion.div
              style={{
                position: "absolute",
                width: dotSize, height: dotSize,
                borderRadius: "50%",
                background: "#a78bfa",
                top: -orbitR - dotSize / 2,
                left: -dotSize / 2,
              }}
              initial={{ opacity: 0 }}
              animate={{ opacity: [0.6, 1, 0.6] }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.25 }}
            />
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Face SVG */}
      <motion.svg
        width={size} height={size} viewBox="0 0 80 80" fill="none"
        xmlns="http://www.w3.org/2000/svg"
        animate={
          isThinking ? { scale: 0.88, y: 0 } :
          isSpeaking ? { scale: [1, 1.04, 1], y: 0 } :
                       { y: [0, -5, 0] }
        }
        transition={
          isThinking ? { duration: 0.2 } :
          isSpeaking ? { duration: 0.75, repeat: Infinity, ease: "easeInOut" } :
                       { duration: 3.5, repeat: Infinity, ease: "easeInOut" }
        }
      >
        <defs>
          <radialGradient id={`face-${uid}`} cx="42%" cy="32%" r="62%">
            <stop offset="0%" stopColor="#c4b5fd" />
            <stop offset="55%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#6d28d9" />
          </radialGradient>
          <radialGradient id={`shine-${uid}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="white" stopOpacity="0.32" />
            <stop offset="100%" stopColor="white" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Head */}
        <circle cx="40" cy="40" r="37" fill={`url(#face-${uid})`} />

        {/* Shine highlight */}
        <ellipse cx="27" cy="21" rx="11" ry="7" fill={`url(#shine-${uid})`} />

        {/* Blush */}
        <ellipse cx="17" cy="51" rx="8.5" ry="5.5" fill="#fda4af" fillOpacity="0.45" />
        <ellipse cx="63" cy="51" rx="8.5" ry="5.5" fill="#fda4af" fillOpacity="0.45" />

        {/* Eyes — normal */}
        {!isThinking && (
          <>
            <motion.g
              style={{ transformOrigin: "27px 37px" }}
              animate={{ scaleY: [1, 1, 1, 0.07, 1, 1] }}
              transition={{ duration: 5, repeat: Infinity, repeatDelay: 1.5, ease: "easeInOut" }}
            >
              <ellipse cx="27" cy="37" rx="5.5" ry="7" fill="white" />
              <circle cx="28.5" cy="38.5" r="3.8" fill="#2d2640" />
              <circle cx="30.5" cy="36.5" r="1.6" fill="white" />
            </motion.g>
            <motion.g
              style={{ transformOrigin: "53px 37px" }}
              animate={{ scaleY: [1, 1, 1, 0.07, 1, 1] }}
              transition={{ duration: 5, repeat: Infinity, repeatDelay: 1.5, ease: "easeInOut" }}
            >
              <ellipse cx="53" cy="37" rx="5.5" ry="7" fill="white" />
              <circle cx="54.5" cy="38.5" r="3.8" fill="#2d2640" />
              <circle cx="56.5" cy="36.5" r="1.6" fill="white" />
            </motion.g>
          </>
        )}

        {/* Thinking eyes — curved upward arcs */}
        {isThinking && (
          <>
            <path d="M22 39 Q27 33 32 39" stroke="white" strokeWidth="2.8" strokeLinecap="round" fill="none" />
            <path d="M48 39 Q53 33 58 39" stroke="white" strokeWidth="2.8" strokeLinecap="round" fill="none" />
          </>
        )}

        {/* Tiny nose */}
        <circle cx="40" cy="47" r="1.8" fill="white" fillOpacity="0.4" />

        {/* Mouth */}
        <motion.path
          stroke="white" strokeWidth="2.8" strokeLinecap="round" fill="none"
          d={isSpeaking ? "M29 55 Q40 66 51 55" : "M32 55 Q40 62 48 55"}
          animate={isSpeaking ? {
            d: ["M29 55 Q40 66 51 55", "M29 57 Q40 60 51 57", "M29 55 Q40 66 51 55"],
          } : {}}
          transition={{ duration: 0.42, repeat: isSpeaking ? Infinity : 0, ease: "easeInOut" }}
        />

        {/* Floating 💙 on idle */}
        <AnimatePresence>
          {state === "idle" && (
            <motion.text
              key="heart" x="53" y="12" fontSize="10" textAnchor="middle"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: [0, 1, 1, 0], y: [20, 8, 8, -2] }}
              exit={{ opacity: 0 }}
              transition={{ duration: 4.5, repeat: Infinity, repeatDelay: 5 }}
            >
              💙
            </motion.text>
          )}
        </AnimatePresence>
      </motion.svg>
    </div>
  );
}
