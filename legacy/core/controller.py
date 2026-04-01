import json
from typing import Dict, Any, List
from tools import *

class Controller:
    """
    Stage 2: Agentic Controller.
    Decides which tools to call based on the user's message and safety status.
    """
    
    def __init__(self, llm_client, tool_registry: Dict[str, BaseTool]):
        self.llm = llm_client
        self.tool_registry = tool_registry
        self.system_prompt = """You are the Controller Agent for a mental health support chatbot.

CRITICAL: Output ONLY valid JSON. No explanations, no markdown, no extra text.

ROLE: Decide which tools to call to best respond to the user's message.

CONSTRAINTS:
- Safety checks (crisis, moderation) ALREADY RAN - you cannot bypass them
- You may call ANY tool from the registry EXCEPT system-only tools
- Output ONLY valid JSON (no markdown, no explanations, no code blocks)
- Prefer fewer tool calls if not needed
- Always end with "MasterResponderTool" as final_action

AVAILABLE TOOLS:
{tool_descriptions}

INPUT:
{{
"user_message": {{user_message_text}},
"risk_level": {{risk_level}},
"session_summary": {{session_summary}}
}}

TASK:
Analyze the user's message and decide which tools to call.

OUTPUT FORMAT (STRICT JSON, NO MARKDOWN):
{{
"tool_sequence": [
{{"name": "ToolName1", "input": {{}}, "reason": "why calling this"}},
{{"name": "ToolName2", "input": {{}}, "reason": "why calling this"}}
],
"final_action": "MasterResponderTool",
"overall_strategy": "brief 1-sentence explanation of approach"
}}

REMEMBER: Output ONLY the JSON object above. No ```json``` markers, no explanations.
"""

    def _get_tool_descriptions(self) -> str:
        descriptions = []
        for name, tool in self.tool_registry.items():
            descriptions.append(f"- {name}: {tool.description}")
        return "\n".join(descriptions)

    def decide(self, user_input: str, risk_level: str, session_summary: str) -> Dict[str, Any]:
        """
        Decide on the tool sequence.
        """
        tool_desc = self._get_tool_descriptions()
        prompt = self.system_prompt.format(
            tool_descriptions=tool_desc,
            user_message_text=json.dumps(user_input),
            risk_level=risk_level,
            session_summary=session_summary
        )
        
        response = self.llm.generate(prompt, max_tokens=500, temperature=0.0) # Low temp for deterministic JSON
        
        text = ""
        if isinstance(response, dict):
             if 'choices' in response and response['choices']:
                text = response['choices'][0]['message']['content']
             elif 'candidates' in response and response['candidates']:
                text = response['candidates'][0]['content']['parts'][0]['text']
        else:
            text = str(response)
        
        # Clean up and extract JSON
        text = text.strip()
        
        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Try to extract JSON object if there's extra text
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            text = json_match.group(0)
        
        try:
            plan = json.loads(text)
            
            # Validate plan structure
            if not isinstance(plan.get('tool_sequence'), list):
                raise ValueError("tool_sequence must be a list")
            if 'final_action' not in plan:
                plan['final_action'] = 'MasterResponderTool'
            
            return plan
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback plan if JSON fails
            print(f"⚠️  Error parsing JSON plan: {str(e)[:100]}")
            print(f"Raw response (first 200 chars): {text[:200]}")
            return {
                "tool_sequence": [],
                "final_action": "MasterResponderTool",
                "overall_strategy": "Fallback: Direct response due to parse error"
            }
