import os
import requests
from typing import Dict, Any


class LLMClient:
    """Base LLM client interface."""
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()


class GroqClient(LLMClient):
    def __init__(self, api_key: str = None, api_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.api_url = api_url or os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1")
        # Use smaller, faster model for RAG-enhanced agents
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required for GroqClient")

    def generate(self, prompt: str, max_tokens: int = 512, messages: list = None, temperature: float = None) -> Dict[str, Any]:
        url = f"{self.api_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        # Use messages if provided (for conversation history), otherwise use prompt
        if messages:
            message_list = messages
        else:
            message_list = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": self.model,
            "messages": message_list,
            "max_tokens": max_tokens,
            "temperature": temperature if temperature is not None else 0.85
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()


class GeminiClient(LLMClient):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiClient")

    def generate(self, prompt: str, max_tokens: int = 512, messages: list = None, temperature: float = None) -> Dict[str, Any]:
        # Gemini uses API key as query parameter
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}
        
        # Convert messages to Gemini format if provided
        if messages:
            contents = []
            for msg in messages:
                role = "user" if msg["role"] in ["user", "User"] else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        else:
            contents = [{"parts": [{"text": prompt}]}]
        
        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature if temperature is not None else 0.85}
        }
        resp = requests.post(url, json=payload, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
