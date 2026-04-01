from typing import Dict, Any
from .base import BaseTool
from conversation_memory import ConversationMemory

class MemoryReadTool(BaseTool):
    def __init__(self, llm_client):
        super().__init__(
            name="MemoryReadTool",
            description="Fetch sanitized session summary and history"
        )
        self.memory = ConversationMemory(llm_client)

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # In a real implementation, we would use session_id to load specific memory
        # For now, we assume the global memory instance or a passed one
        
        summary = self.memory.get_context_for_llm()
        recent_messages = self.memory.get_recent_messages(5)
        
        return {
            "session_summary": summary,
            "recent_history": [
                {"role": m["role"], "content": m["content"]} 
                for m in recent_messages
            ]
        }
