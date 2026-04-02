"use client";

import {
  useState, useEffect, useRef, useCallback, KeyboardEvent,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import { v4 as uuidv4 } from "uuid";
import Avatar, { AvatarState } from "@/components/Avatar";
import TypingIndicator from "@/components/TypingIndicator";
import MoodArc, { MoodEntry } from "@/components/MoodArc";

/* ─── Types ──────────────────────────────────────── */

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  ts: number;
}

interface StoredSession {
  id: string;
  startedAt: number;
  preview: string;
  messages: Message[];
  moodHistory: MoodEntry[];
}

type ApiResponse = {
  response: string;
  emotions: string[];
  risk_level: "low" | "medium" | "high";
  referral_needed: boolean;
  session_id: string;
  metrics: Record<string, unknown>;
};

/* ─── Helpers ─────────────────────────────────────── */

const GREETING: Message = {
  id: "greeting",
  role: "assistant",
  content: "hey, glad you're here 💙 kya scene hai aaj?",
  ts: Date.now(),
};

function formatDate(ts: number): string {
  const d = new Date(ts);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function ls<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; }
  catch { return fallback; }
}

function lsSet(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
}

/* ─── Main component ─────────────────────────────── */

export default function Home() {
  const [userId,      setUserId]      = useState<string>("");
  const [sessionId,   setSessionId]   = useState<string>("");
  const [messages,    setMessages]    = useState<Message[]>([GREETING]);
  const [moodHistory, setMoodHistory] = useState<MoodEntry[]>([]);
  const [sessions,    setSessions]    = useState<StoredSession[]>([]);
  const [avatarState, setAvatarState] = useState<AvatarState>("idle");
  const [loading,     setLoading]     = useState(false);
  const [input,       setInput]       = useState("");
  const [showMetrics, setShowMetrics] = useState(false);
  const [lastMetrics, setLastMetrics] = useState<Record<string, unknown> | null>(null);

  const bottomRef   = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /* Init from localStorage */
  useEffect(() => {
    // user_id persists across sessions (identity)
    let uid = ls<string>("mhc_uid", "");
    if (!uid) { uid = uuidv4(); lsSet("mhc_uid", uid); }
    setUserId(uid);

    // session_id is ALWAYS fresh on page load — never reuse old session.
    // Reusing mhc_sid caused the backend to load old history/risk into a
    // visually-fresh conversation (session isolation leakage).
    const sid = uuidv4();
    setSessionId(sid);

    setSessions(ls<StoredSession[]>("mhc_sessions", []));
  }, []);

  /* Auto-scroll */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  /* Auto-resize textarea */
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
  }, [input]);

  /* Send message */
  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading || !sessionId) return;

    setInput("");
    const userMsg: Message = { id: uuidv4(), role: "user", content: text, ts: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    setAvatarState("thinking");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, user_id: userId, session_id: sessionId }),
      });
      const data: ApiResponse = await res.json();

      setAvatarState("speaking");
      setTimeout(() => setAvatarState("idle"), 2800);

      let reply = data.response;
      if (data.risk_level === "high") {
        reply += "\n\n💙 Professional support:\n• iCall: 9152987821\n• Vandrevala: 1860-2662-345";
      }

      const mahiMsg: Message = { id: uuidv4(), role: "assistant", content: reply, ts: Date.now() };
      setMessages(prev => [...prev, mahiMsg]);

      const newEntry: MoodEntry = {
        turn: moodHistory.length + 1,
        risk_level: data.risk_level,
        emotions: data.emotions,
      };
      setMoodHistory(prev => [...prev, newEntry]);
      setLastMetrics(data.metrics);
    } catch {
      setAvatarState("idle");
      setMessages(prev => [...prev, {
        id: uuidv4(), role: "assistant",
        content: "server se connect nahi ho pa raha. backend chalu hai?",
        ts: Date.now(),
      }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, sessionId, userId, moodHistory.length]);

  /* New session */
  const handleNewSession = useCallback(() => {
    // Save current session
    if (messages.length > 1) {
      const firstUser = messages.find(m => m.role === "user");
      const saved: StoredSession = {
        id: sessionId,
        startedAt: messages[0].ts,
        preview: firstUser?.content.slice(0, 55) ?? "New session",
        messages,
        moodHistory,
      };
      const updated = [saved, ...sessions].slice(0, 20);
      setSessions(updated);
      lsSet("mhc_sessions", updated);
    }

    const sid = uuidv4();
    setSessionId(sid);
    // Don't persist to localStorage — page load always starts fresh
    setMessages([{ ...GREETING, id: uuidv4(), ts: Date.now() }]);
    setMoodHistory([]);
    setLastMetrics(null);
    setInput("");
    setAvatarState("idle");
  }, [messages, moodHistory, sessionId, sessions]);

  /* Load past session — shows old messages in UI but forks to a fresh session_id
     so old risk/history doesn't contaminate backend routing for new messages */
  const handleLoadSession = (s: StoredSession) => {
    const freshSid = uuidv4();
    setSessionId(freshSid);
    setMessages(s.messages);
    setMoodHistory(s.moodHistory);
  };

  /* Keyboard */
  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  /* ─── Render ──────────────────────────────────── */
  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg)" }}>

      {/* ══════════════ SIDEBAR ══════════════ */}
      <aside
        className="flex flex-col flex-shrink-0 overflow-hidden"
        style={{
          width: 264,
          background: "var(--sidebar)",
          borderRight: "1px solid var(--sidebar-b)",
        }}
      >
        {/* Branding */}
        <div className="flex flex-col items-center pt-8 pb-6 px-5">
          <Avatar state={avatarState} size={72} />
          <h1
            className="mt-3 text-xl font-semibold tracking-tight"
            style={{ fontFamily: "Lora, serif", color: "var(--text-1)" }}
          >
            Mahi
          </h1>
          <p className="text-xs mt-0.5 text-center leading-relaxed" style={{ color: "var(--text-2)" }}>
            Ek safe space —<br />apni baat karo, bina judge ke.
          </p>
        </div>

        {/* New Session */}
        <div className="px-4 pb-4">
          <button
            onClick={handleNewSession}
            className="w-full py-2.5 rounded-xl text-sm font-semibold transition-all duration-150
                       hover:opacity-90 active:scale-95"
            style={{
              background: "var(--accent)",
              color: "white",
              boxShadow: "0 4px 14px rgba(124,106,245,0.35)",
            }}
          >
            + New Session
          </button>
        </div>

        <div style={{ height: 1, background: "var(--sidebar-b)", margin: "0 16px" }} />

        {/* Scrollable middle */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">

          {/* Session history */}
          {sessions.length > 0 && (
            <section>
              <p className="text-[10px] uppercase tracking-widest font-semibold mb-2"
                 style={{ color: "var(--text-3)" }}>
                Sessions
              </p>
              <div className="space-y-1.5">
                {sessions.map(s => (
                  <button
                    key={s.id}
                    onClick={() => handleLoadSession(s)}
                    className="w-full text-left px-3 py-2.5 rounded-xl transition-all duration-100
                               hover:bg-white/70 group"
                    style={s.id === sessionId ? { background: "white", boxShadow: "0 2px 8px rgba(44,38,64,0.07)" } : {}}
                  >
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-[10px] font-semibold" style={{ color: "var(--text-3)" }}>
                        {formatDate(s.startedAt)}
                      </span>
                      <div className="flex gap-1">
                        {s.moodHistory.slice(-3).map((m, i) => (
                          <div key={i} className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                               style={{ background: m.risk_level === "low" ? "#34d399" : m.risk_level === "medium" ? "#fbbf24" : "#f87171" }} />
                        ))}
                      </div>
                    </div>
                    <p className="text-xs truncate" style={{ color: "var(--text-1)" }}>{s.preview}</p>
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* Current session mood */}
          <section>
            <p className="text-[10px] uppercase tracking-widest font-semibold mb-2"
               style={{ color: "var(--text-3)" }}>
              This session
            </p>
            <MoodArc history={moodHistory} />
          </section>
        </div>

        {/* Debug toggle */}
        <div className="px-4 pb-4 pt-2" style={{ borderTop: "1px solid var(--sidebar-b)" }}>
          <button
            onClick={() => setShowMetrics(v => !v)}
            className="text-[10px] transition-colors"
            style={{ color: "var(--text-3)" }}
          >
            {showMetrics ? "hide" : "show"} metrics
          </button>
        </div>
      </aside>

      {/* ══════════════ MAIN ══════════════ */}
      <main className="flex-1 flex flex-col overflow-hidden">

        {/* Header */}
        <header
          className="flex items-center gap-3 px-6 py-3 flex-shrink-0"
          style={{
            background: "rgba(250,248,245,0.85)",
            backdropFilter: "blur(12px)",
            borderBottom: "1px solid #ebe6f7",
          }}
        >
          <Avatar state={avatarState} size={38} />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm" style={{ color: "var(--text-1)", fontFamily: "Lora, serif" }}>
                Mahi
              </span>
              <span className="w-2 h-2 rounded-full" style={{ background: "#34d399" }} />
            </div>
            <p className="text-xs" style={{ color: "var(--text-2)" }}>
              {loading ? "typing…" : "always here for you"}
            </p>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto dot-grid px-6 py-6 space-y-4">
          <AnimatePresence initial={false}>
            {messages.map(msg => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className={`flex items-end gap-2.5 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                {msg.role === "assistant" && <Avatar state="idle" size={32} />}

                <div
                  className="max-w-[65%] text-sm leading-relaxed whitespace-pre-wrap"
                  style={
                    msg.role === "user"
                      ? {
                          background: "var(--user-bg)",
                          color: "white",
                          padding: "10px 16px",
                          borderRadius: "18px 18px 4px 18px",
                          boxShadow: "0 4px 14px rgba(99,102,241,0.28)",
                          fontWeight: 500,
                        }
                      : {
                          background: "white",
                          color: "var(--text-1)",
                          padding: "12px 16px",
                          borderRadius: "4px 18px 18px 18px",
                          boxShadow: "0 2px 12px rgba(44,38,64,0.07)",
                          borderLeft: "3px solid var(--accent-2, #c4b5fd)",
                        }
                  }
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
                exit={{ opacity: 0 }}
                className="flex items-end gap-2.5"
              >
                <Avatar state="thinking" size={32} />
                <TypingIndicator />
              </motion.div>
            )}
          </AnimatePresence>

          <div ref={bottomRef} />
        </div>

        {/* Metrics panel */}
        <AnimatePresence>
          {showMetrics && lastMetrics && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden flex-shrink-0"
              style={{ borderTop: "1px solid #ebe6f7", background: "#faf8f5" }}
            >
              <pre className="px-6 py-3 text-[10px] font-mono overflow-x-auto" style={{ color: "var(--text-2)" }}>
                {JSON.stringify(lastMetrics, null, 2)}
              </pre>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Input */}
        <div
          className="flex-shrink-0 px-6 py-4"
          style={{ borderTop: "1px solid #ebe6f7", background: "rgba(250,248,245,0.95)" }}
        >
          <div
            className="flex items-end gap-3 rounded-2xl px-4 py-3"
            style={{ background: "white", boxShadow: "0 2px 16px rgba(44,38,64,0.08)" }}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Kya chal raha hai?"
              rows={1}
              disabled={loading}
              className="flex-1 resize-none outline-none text-sm bg-transparent"
              style={{
                color: "var(--text-1)",
                maxHeight: 120,
                scrollbarWidth: "none",
                lineHeight: "1.5",
              }}
            />
            <motion.button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              whileTap={{ scale: 0.92 }}
              className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-opacity"
              style={{
                background: input.trim() ? "var(--accent)" : "#e2dff8",
                boxShadow: input.trim() ? "0 4px 12px rgba(124,106,245,0.38)" : "none",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M2 8L14 2L10 8L14 14L2 8Z" fill={input.trim() ? "white" : "#a78bfa"} />
              </svg>
            </motion.button>
          </div>
          <p className="text-center text-[10px] mt-2" style={{ color: "var(--text-3)" }}>
            Not a replacement for professional mental health care
          </p>
        </div>
      </main>
    </div>
  );
}
