"use client";

import { motion } from "framer-motion";

interface MoodEntry {
  turn: number;
  risk_level: "low" | "medium" | "high";
  emotions: string[];
}

const RISK_COLOR = {
  low:    "bg-emerald-400",
  medium: "bg-amber-400",
  high:   "bg-rose-500",
};

const RISK_LABEL = { low: "calm", medium: "stressed", high: "crisis" };

export default function MoodArc({ history }: { history: MoodEntry[] }) {
  if (!history.length) return null;

  return (
    <div className="px-4 py-3 border-t border-surface-600">
      <p className="text-xs text-gray-500 mb-2 uppercase tracking-wide">Mood this session</p>
      <div className="flex items-center gap-1.5 flex-wrap">
        {history.map((entry, i) => (
          <motion.div
            key={i}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            title={`Turn ${entry.turn}: ${RISK_LABEL[entry.risk_level]}${entry.emotions.length ? " · " + entry.emotions.join(", ") : ""}`}
            className={`w-3 h-3 rounded-full cursor-default ${RISK_COLOR[entry.risk_level]}`}
          />
        ))}
      </div>
    </div>
  );
}
