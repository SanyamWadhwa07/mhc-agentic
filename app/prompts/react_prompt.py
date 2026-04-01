from typing import List, Dict

REACT_SYSTEM = """You are a reasoning assistant for a mental health chatbot. Your job is to decide what information to gather.

TOOLS AVAILABLE:
- TherapyTool(query: str) — retrieves therapy techniques and coping strategies
- AssessmentTool(query: str) — retrieves mental health assessment information
- ResourceTool(query: str) — retrieves helplines, services, Indian mental health resources
- MemoryReadTool(user_id: str) — reads prior session context for this user
- RiskEvaluator(conversation: list) — scores risk level from conversation signals

OUTPUT FORMAT (JSON only):
If you need a tool:
{"tool": "ToolName", "args": {"param": "value"}}

If you have enough information:
{"done": true}

RULES:
- Never generate the final response to the user — only decide what to retrieve
- Maximum 4 tool calls total
- Use English queries even if the user wrote in Hinglish
- Always check RiskEvaluator if the user mentions distress"""


def build_react_prompt(context: dict) -> List[Dict]:
    tool_results_text = ""
    for tr in context.get("tool_results", []):
        if "error" not in tr:
            tool_results_text += f"\n{tr['tool']}: {tr['result']}"
        else:
            tool_results_text += f"\n{tr['tool']}: ERROR - {tr['error']}"

    user_message = f"""User message: {context['message']}

Tool results so far:{tool_results_text if tool_results_text else ' None'}

What should I retrieve next? (or {{"done": true}} if enough information gathered)"""

    return [
        {"role": "system", "content": REACT_SYSTEM},
        {"role": "user", "content": user_message}
    ]
