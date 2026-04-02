"use client";
import { useState } from "react";
import { motion } from "framer-motion";

export interface MoodEntry {
  turn: number;
  risk_level: "low" | "medium" | "high";
  emotions: string[];
}

const COLORS = { low: "#34d399", medium: "#fbbf24", high: "#f87171" };
const LABELS = { low: "Calm", medium: "Stressed", high: "Crisis" };

export default function MoodArc({ history }: { history: MoodEntry[] }) {
  const [hovered, setHovered] = useState<number | null>(null);

  if (!history.length) return (
    <p className="text-xs text-[var(--text-3)] italic mt-1">No messages yet</p>
  );

  return (
    <div className="flex flex-wrap gap-1.5 mt-1">
      {history.map((entry, i) => (
        <div key={i} className="relative">
          <motion.div
            className="dot-pop w-3.5 h-3.5 rounded-full cursor-default"
            style={{ background: COLORS[entry.risk_level] }}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 400, damping: 15 }}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
          />
          {hovered === i && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-20
                         bg-[var(--text-1)] text-white text-[10px] rounded-lg px-2.5 py-1.5
                         whitespace-nowrap shadow-lg pointer-events-none"
            >
              <div className="font-semibold">{LABELS[entry.risk_level]}</div>
              {entry.emotions.length > 0 && (
                <div className="text-[var(--text-3)] mt-0.5">{entry.emotions.join(", ")}</div>
              )}
              {/* Arrow */}
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4
                              border-transparent border-t-[var(--text-1)]" />
            </motion.div>
          )}
        </div>
      ))}
    </div>
  );
}
