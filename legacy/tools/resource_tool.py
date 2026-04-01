from typing import Dict, Any
from .base import BaseTool
from knowledge_base import KnowledgeBase

class ResourceTool(BaseTool):
    def __init__(self, llm_client):
        super().__init__(
            name="ResourceTool",
            description="Consult a resource expert for professional help options (uses RAG)"
        )
        self.llm = llm_client
        self.knowledge_base = KnowledgeBase('resource')
        self.system_prompt = """You are a mental health resource expert specializing in connecting people to professional help.
Your expertise includes: types of mental health professionals, therapy modalities, insurance navigation,
support groups, community resources, and treatment options.

=== TASK ===
Provide ONE brief insight (1-2 sentences max) based on your expertise.
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
        
        # Extract text
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
