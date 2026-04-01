from typing import Dict, Any
from .base import BaseTool

class MasterResponderTool(BaseTool):
    def __init__(self, llm_client):
        super().__init__(
            name="MasterResponderTool",
            description="Generate final therapeutic response"
        )
        self.llm = llm_client

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # This tool is special - it generates the final response
        # It expects the full context to be passed to it
        prompt_context = input_data.get("prompt_context", "")
        
        # We'll use a simple generation here, the complexity is in the prompt construction
        # which happens in the Controller/Orchestrator before calling this tool
        
        resp = self.llm.generate(prompt_context, max_tokens=150, temperature=0.7)
        
        # Handle different client response formats
        text = ""
        if isinstance(resp, dict):
             if 'choices' in resp and resp['choices']:
                text = resp['choices'][0]['message']['content']
             elif 'candidates' in resp and resp['candidates']:
                text = resp['candidates'][0]['content']['parts'][0]['text']
        else:
            text = str(resp)

        return {
            "reply_text": text
        }
