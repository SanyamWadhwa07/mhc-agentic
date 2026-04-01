from typing import Dict, Any
from .base import BaseTool
from knowledge_base import KnowledgeBase

class TherapyTool(BaseTool):
    def __init__(self, llm_client):
        super().__init__(
            name="TherapyTool",
            description="Consult a therapy expert for coping strategies (uses RAG)"
        )
        self.llm = llm_client
        self.knowledge_base = KnowledgeBase('therapy')
        self.system_prompt = """You are a supportive friend with expertise in coping strategies and mental wellness.
Your role is to suggest helpful coping strategies in a friendly, accessible way.
Share practical techniques people can try right away. Validate feelings and normalize struggles.
Use the knowledge provided but translate it into warm, everyday language.

=== TASK ===
Provide ONE brief insight (1-2 sentences max) based on your expertise and the context.
No lists, just the key point.
"""

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_input = input_data.get("text", "")
        
        # 1. Retrieve Context
        context_docs = self.knowledge_base.search(user_input, top_k=3)
        
        # 2. Build Prompt
        prompt = f"{self.system_prompt}\n\n=== USER MESSAGE ===\n{user_input}\n"
        
        if context_docs:
            prompt += "\n=== RELEVANT KNOWLEDGE ===\n"
            for i, doc in enumerate(context_docs, 1):
                prompt += f"[Knowledge {i}] {doc['title']}\n{doc['content']}\n"
        
        prompt += "\n=== YOUR CONTRIBUTION ===\n"
        
        # 3. Generate
        resp = self.llm.generate(prompt, max_tokens=100, temperature=0.7)
        
        # Extract text (simplified helper)
        text = str(resp)
        if isinstance(resp, dict):
             if 'choices' in resp and resp['choices']:
                text = resp['choices'][0]['message']['content']
             elif 'candidates' in resp and resp['candidates']:
                text = resp['candidates'][0]['content']['parts'][0]['text']
        
        return {
            "contribution": text,
            "context_used": [doc['title'] for doc in context_docs]
        }
