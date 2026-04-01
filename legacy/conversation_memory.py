"""
Conversation memory management with automatic summarization and storage.
Maintains full chat history and creates summaries after every 10 messages.
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any


class ConversationMemory:
    """Manages conversation history with automatic summarization."""
    
    def __init__(self, llm_client, session_id: str = None):
        self.llm = llm_client
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.messages: List[Dict[str, Any]] = []
        self.summaries: List[str] = []
        self.message_count = 0
        self.summary_interval = 10
        
        # Create storage directory
        os.makedirs('sessions', exist_ok=True)
        self.session_file = f'sessions/{self.session_id}.json'
        
        # Load existing session if present
        self._load_session()
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add a message to conversation history."""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self.messages.append(message)
        self.message_count += 1
        
        # Auto-summarize every 10 messages
        if self.message_count % self.summary_interval == 0:
            self._create_summary()
        
        self._save_session()
    
    def _create_summary(self):
        """Create summary of recent conversation."""
        # Get last 10 messages for summary
        recent_messages = self.messages[-self.summary_interval:]
        
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in recent_messages
        ])
        
        summary_prompt = f"""Summarize this mental health conversation in 2-3 sentences.
Focus on: main concerns discussed, symptoms mentioned, interventions suggested, user's emotional state.

Conversation:
{conversation_text}

Summary:"""
        
        resp = self.llm.generate(summary_prompt, max_tokens=150)
        summary = self._extract_text(resp)
        
        self.summaries.append({
            'timestamp': datetime.now().isoformat(),
            'message_range': f"{len(self.messages) - self.summary_interval + 1}-{len(self.messages)}",
            'summary': summary
        })
        
        self._save_session()
    
    def get_recent_messages(self, count: int = 6) -> List[Dict[str, Any]]:
        """Get recent messages for NLP analysis."""
        if not self.messages:
            return []
        recent_start = max(0, len(self.messages) - count)
        return self.messages[recent_start:]
    
    def get_context_for_llm(self) -> str:
        """Get optimized context for LLM (summaries + recent messages)."""
        context_parts = []
        
        # Add all summaries for long-term context
        if self.summaries:
            context_parts.append("=== CONVERSATION HISTORY SUMMARIES ===")
            for i, summary in enumerate(self.summaries, 1):
                context_parts.append(f"Summary {i}: {summary['summary']}")
        
        # Add recent messages (last 6-8)
        if len(self.messages) > 0:
            context_parts.append("\n=== RECENT CONVERSATION ===")
            recent_start = max(0, len(self.messages) - 6)
            for msg in self.messages[recent_start:]:
                context_parts.append(f"{msg['role']}: {msg['content'][:200]}")
        
        return "\n".join(context_parts)
    
    def _save_session(self):
        """Save session to disk."""
        session_data = {
            'session_id': self.session_id,
            'messages': self.messages,
            'summaries': self.summaries,
            'message_count': self.message_count,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
    
    def _load_session(self):
        """Load existing session from disk."""
        if os.path.exists(self.session_file):
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                self.messages = session_data.get('messages', [])
                self.summaries = session_data.get('summaries', [])
                self.message_count = session_data.get('message_count', 0)
    
    def _extract_text(self, resp: Dict[str, Any]) -> str:
        """Extract text from LLM response."""
        if isinstance(resp, dict):
            if 'choices' in resp and resp['choices']:
                choice = resp['choices'][0]
                if 'message' in choice:
                    return choice['message'].get('content', '')
                elif 'text' in choice:
                    return choice['text']
            elif 'candidates' in resp and resp['candidates']:
                candidate = resp['candidates'][0]
                if 'content' in candidate:
                    content = candidate['content']
                    if 'parts' in content and content['parts']:
                        return content['parts'][0].get('text', '')
        return str(resp)
