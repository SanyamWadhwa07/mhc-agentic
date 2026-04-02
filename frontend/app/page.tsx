"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { v4 as uuidv4 } from "uuid";
import Avatar, { AvatarState } from "@/components/Avatar";
import TypingIndicator from "@/components/TypingIndicator";
import MoodArc from "@/components/MoodArc";
import { sendMessage, type ChatResponse } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  referral?: boolean;
}

interface MoodEntry {
  turn: number;
  risk_level: "low" | "medium" | "high";
  emotions: string[];
}

const GREETING = "hey, glad you're here 💙 kya scene hai aaj?";

function getStoredId(key: string): string {
  if (typeof window === "undefined") return uuidv4();
  const stored = sessionStorage.getItem(key);
  if (stored) return stored;
  const fresh = uuidv4();
  sessionStorage.setItem(key, fresh);
  return fresh;
}

export default function Home() {
  const [userId]    = useState<string>(() => getStoredId("mhc_user_id"));
  const [sessionId, setSessionId] = useState<string>(() => getStoredId("mhc_session_id"));
  const [messages, setMessages]   = useState<Message[]>([
    { id: uuidv4(), role: "assistant", content: GREETING },
  ]);
  const [moodHistory, setMoodHistory] = useState<MoodEntry[]>([]);
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const [avatarState, setAvatarState] = useState<AvatarState>("idle");
  const [showMetrics, setShowMetrics] = useState(false);
  const [lastMetrics, setLastMetrics] = useState<Record<string, unknown> | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages(prev => [...prev, { id: uuidv4(), role: "user", content: text }]);
    setLoading(true);
    setAvatarState("thinking");

    try {
      const data: ChatResponse = await sendMessage(text, userId, sessionId);

      setAvatarState("speaking");
      setTimeout(() => setAvatarState("idle"), 2500);

      const reply = data.referral_needed
        ? `${data.response}\n\n💙 **Professional support:**\niCall: 9152987821\nVandrevala: 1860-2662-345`
        : data.response;

      setMessages(prev => [
        ...prev,
        { id: uuidv4(), role: "assistant", content: reply, referral: data.referral_needed },
      ]);

      setMoodHistory(prev => [
        ...prev,
        {
          turn: prev.length + 1,
          risk_level: data.risk_level,
          emotions: data.emotions,
        },
      ]);

      setLastMetrics(data.metrics);
    } catch {
      setAvatarState("idle");
      setMessages(prev => [
        ...prev,
        { id: uuidv4(), role: "assistant", content: "server se connect nahi ho pa raha. backend chalu hai?" },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, userId, sessionId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewSession = () => {
    const newSid = uuidv4();
    sessionStorage.setItem("mhc_session_id", newSid);
    setSessionId(newSid);
    setMessages([{ id: uuidv4(), role: "assistant", content: "hey, acha laga phir se milke 😊 kuch share karna hai?" }]);
    setMoodHistory([]);
    setLastMetrics(null);
  };

  return (
    <div className="flex flex-col h-screen bg-surface-900 max-w-2xl mx-auto">
      {/* ── Header ── */}
      <header className="flex items-center gap-3 px-5 py-4 border-b border-surface-600 bg-surface-800">
        <Avatar state={avatarState} size={52} />
        <div className="flex-1 min-w-0">
          <h1 className="font-semibold text-white text-base leading-tight">Mahi</h1>
          <p className="text-xs text-gray-400 truncate">
            {loading ? "typing…" : "Ek safe space — bina judge ke."}
          </p>
        </div>
        <button
          onClick={handleNewSession}
          className="text-xs text-gray-500 hover:text-mahi-400 transition-colors px-2 py-1 rounded-lg hover:bg-surface-700"
        >
          New session
        </button>
      </header>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        <AnimatePresence initial={false}>
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22 }}
              className={`flex items-end gap-2 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              {/* Avatar only on assistant messages */}
              {msg.role === "assistant" && (
                <div className="flex-shrink-0 mb-1">
                  <Avatar state="idle" size={32} />
                </div>
              )}

              <div
                className={`max-w-[78%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-mahi-600 text-white rounded-br-sm"
                    : "bg-surface-700 text-gray-100 rounded-bl-sm"
                }`}
              >
                {msg.content}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing indicator */}
        <AnimatePresence>
          {loading && (
            <motion.div
              key="typing"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              className="flex items-end gap-2"
            >
              <Avatar state="thinking" size={32} />
              <TypingIndicator />
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={bottomRef} />
      </div>

      {/* ── Mood Arc ── */}
      <MoodArc history={moodHistory} />

      {/* ── Debug metrics ── */}
      <AnimatePresence>
        {showMetrics && lastMetrics && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-surface-600 bg-surface-800 text-xs text-gray-400 font-mono"
          >
            <pre className="px-4 py-3 overflow-x-auto">
              {JSON.stringify(lastMetrics, null, 2)}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Input ── */}
      <div className="px-4 pb-5 pt-3 border-t border-surface-600 bg-surface-800">
        <div className="flex items-end gap-3 bg-surface-700 rounded-2xl px-4 py-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Kya chal raha hai?"
            rows={1}
            disabled={loading}
            className="flex-1 bg-transparent resize-none outline-none text-sm text-gray-100 placeholder-gray-500 max-h-32"
            style={{ scrollbarWidth: "none" }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-xl bg-mahi-600 hover:bg-mahi-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 8L14 2L10 8L14 14L2 8Z" fill="white" />
            </svg>
          </button>
        </div>

        {/* Debug toggle */}
        <button
          onClick={() => setShowMetrics(v => !v)}
          className="mt-2 text-[10px] text-gray-600 hover:text-gray-400 transition-colors"
        >
          {showMetrics ? "hide" : "show"} metrics
        </button>
      </div>
    </div>
  );
}
