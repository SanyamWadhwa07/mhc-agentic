"use client";

import { motion } from "framer-motion";

export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3 rounded-2xl rounded-tl-sm bg-surface-700 w-fit">
      {[0, 0.18, 0.36].map((delay, i) => (
        <motion.span
          key={i}
          className="block w-2 h-2 rounded-full bg-mahi-400"
          animate={{ y: [0, -5, 0], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 0.7, repeat: Infinity, delay }}
        />
      ))}
    </div>
  );
}
