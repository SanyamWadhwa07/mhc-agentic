export interface ChatResponse {
  response: string;
  emotions: string[];
  risk_level: "low" | "medium" | "high";
  clinical_flags: string[];
  referral_needed: boolean;
  session_id: string;
  metrics: Record<string, unknown>;
}

export async function sendMessage(
  message: string,
  userId: string,
  sessionId: string
): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, user_id: userId, session_id: sessionId }),
  });

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
