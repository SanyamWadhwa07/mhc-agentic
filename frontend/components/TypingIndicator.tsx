"use client";
import { motion } from "framer-motion";

export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3 bg-white rounded-msg rounded-tl-sm shadow-msg w-fit">
      {[0, 0.18, 0.36].map((delay, i) => (
        <motion.span
          key={i}
          className="block w-2 h-2 rounded-full"
          style={{ background: "#a78bfa" }}
          animate={{ y: [0, -6, 0], opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 0.65, repeat: Infinity, delay, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}
