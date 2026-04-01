from typing import List, Dict, Any


class Agent:
    def __init__(self, llm_client, system_prompt: str = None):
        self.llm = llm_client
        self.memory: List[str] = []
        self.system_prompt = system_prompt or "You are a helpful agent."

    def _build_prompt(self, user_input: str) -> str:
        history = "\n".join(self.memory[-10:])
        return f"{self.system_prompt}\n\nConversation History:\n{history}\n\nUser: {user_input}\nAgent:"

    def step(self, user_input: str) -> Dict[str, Any]:
        prompt = self._build_prompt(user_input)
        resp = self.llm.generate(prompt)
        
        # Normalize response extraction for different providers
        text = None
        if isinstance(resp, dict):
            # Groq/OpenAI format
            if 'choices' in resp and resp['choices']:
                choice = resp['choices'][0]
                if 'message' in choice:
                    text = choice['message'].get('content', '')
                elif 'text' in choice:
                    text = choice['text']
            # Gemini format
            elif 'candidates' in resp and resp['candidates']:
                candidate = resp['candidates'][0]
                if 'content' in candidate:
                    content = candidate['content']
                    if 'parts' in content and content['parts']:
                        text = content['parts'][0].get('text', '')
            # Fallback for other formats
            elif 'output' in resp:
                output = resp.get('output')
                text = str(output) if not isinstance(output, list) else "\n".join(map(str, output))
        
        if text is None:
            text = str(resp)

        # Save to memory
        self.memory.append(f"User: {user_input}")
        self.memory.append(f"Agent: {text}")

        return {"text": text, "raw": resp}
