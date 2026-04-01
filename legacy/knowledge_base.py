"""
Knowledge base and RAG (Retrieval-Augmented Generation) system for mental health agents.
Provides semantic search over specialized knowledge for each agent type.
"""
import json
import numpy as np
from typing import List, Dict, Any, Tuple
import os


class SimpleEmbedding:
    """Simple TF-IDF based embedding for lightweight semantic search without heavy dependencies."""
    
    def __init__(self):
        self.vocabulary = {}
        self.idf = {}
        self.doc_count = 0
    
    def fit(self, documents: List[str]):
        """Build vocabulary and IDF from documents."""
        from collections import Counter
        word_doc_freq = Counter()
        
        for doc in documents:
            words = set(doc.lower().split())
            for word in words:
                word_doc_freq[word] += 1
                if word not in self.vocabulary:
                    self.vocabulary[word] = len(self.vocabulary)
        
        self.doc_count = len(documents)
        for word, freq in word_doc_freq.items():
            self.idf[word] = np.log(self.doc_count / (1 + freq))
    
    def embed(self, text: str) -> np.ndarray:
        """Convert text to TF-IDF vector."""
        from collections import Counter
        words = text.lower().split()
        word_freq = Counter(words)
        
        vector = np.zeros(len(self.vocabulary))
        for word, freq in word_freq.items():
            if word in self.vocabulary:
                idx = self.vocabulary[word]
                tf = freq / len(words)
                vector[idx] = tf * self.idf.get(word, 0)
        
        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector


class KnowledgeBase:
    """Knowledge base with semantic search capabilities."""
    
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.documents: List[Dict[str, Any]] = []
        self.embeddings: List[np.ndarray] = []
        self.embedding_model = SimpleEmbedding()
        self._load_knowledge()
    
    def _load_knowledge(self):
        """Load knowledge from JSON file for this agent type."""
        kb_path = f"knowledge/{self.agent_type}_knowledge.json"
        if os.path.exists(kb_path):
            with open(kb_path, 'r', encoding='utf-8') as f:
                self.documents = json.load(f)
            
            # Build embeddings
            texts = [doc['content'] for doc in self.documents]
            self.embedding_model.fit(texts)
            self.embeddings = [self.embedding_model.embed(text) for text in texts]
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Semantic search for relevant knowledge."""
        if not self.documents:
            return []
        
        query_embedding = self.embedding_model.embed(query)
        
        # Compute cosine similarity
        similarities = []
        for i, doc_embedding in enumerate(self.embeddings):
            similarity = np.dot(query_embedding, doc_embedding)
            similarities.append((similarity, i))
        
        # Sort by similarity
        similarities.sort(reverse=True)
        
        # Return top-k results
        results = []
        for similarity, idx in similarities[:top_k]:
            if similarity > 0.1:  # Threshold
                result = self.documents[idx].copy()
                result['relevance_score'] = float(similarity)
                results.append(result)
        
        return results
    
    def add_document(self, title: str, content: str, metadata: Dict = None):
        """Add a new document to the knowledge base."""
        doc = {
            'title': title,
            'content': content,
            'metadata': metadata or {}
        }
        self.documents.append(doc)
        
        # Update embeddings
        texts = [d['content'] for d in self.documents]
        self.embedding_model.fit(texts)
        self.embeddings = [self.embedding_model.embed(text) for text in texts]
    
    def save(self):
        """Save knowledge base to disk."""
        kb_path = f"knowledge/{self.agent_type}_knowledge.json"
        os.makedirs('knowledge', exist_ok=True)
        with open(kb_path, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, indent=2, ensure_ascii=False)


class RAGAgent:
    """Base agent with RAG capabilities for context-aware responses."""
    
    def __init__(self, llm_client, agent_type: str, system_prompt: str):
        self.llm = llm_client
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.knowledge_base = KnowledgeBase(agent_type)
        self.memory: List[str] = []
    
    def _build_prompt(self, user_input: str, context_docs: List[Dict] = None) -> str:
        """Build prompt with RAG context."""
        history = "\n".join(self.memory[-10:])
        
        prompt_parts = [self.system_prompt]
        
        # Add retrieved knowledge context
        if context_docs:
            prompt_parts.append("\n=== RELEVANT KNOWLEDGE ===")
            for i, doc in enumerate(context_docs, 1):
                prompt_parts.append(f"\n[Context {i}] {doc['title']}")
                prompt_parts.append(f"{doc['content']}")
            prompt_parts.append("\n=== END KNOWLEDGE ===\n")
        
        if history:
            prompt_parts.append(f"\nConversation History:\n{history}")
        
        prompt_parts.append(f"\nUser: {user_input}\nAgent:")
        
        return "\n".join(prompt_parts)
    
    def step(self, user_input: str) -> Dict[str, Any]:
        """Process user input with RAG augmentation."""
        # Retrieve relevant context
        context_docs = self.knowledge_base.search(user_input, top_k=3)
        
        # Build augmented prompt
        prompt = self._build_prompt(user_input, context_docs)
        
        # Generate response
        resp = self.llm.generate(prompt, max_tokens=400)
        
        # Extract text from response
        text = self._extract_text(resp)
        
        # Save to memory
        self.memory.append(f"User: {user_input}")
        self.memory.append(f"Agent: {text}")
        
        return {
            "text": text,
            "raw": resp,
            "context_used": [doc['title'] for doc in context_docs],
            "relevance_scores": [doc.get('relevance_score', 0) for doc in context_docs]
        }
    
    def _extract_text(self, resp: Dict[str, Any]) -> str:
        """Extract text from LLM response."""
        if isinstance(resp, dict):
            # Groq/OpenAI format
            if 'choices' in resp and resp['choices']:
                choice = resp['choices'][0]
                if 'message' in choice:
                    return choice['message'].get('content', '')
                elif 'text' in choice:
                    return choice['text']
            # Gemini format
            elif 'candidates' in resp and resp['candidates']:
                candidate = resp['candidates'][0]
                if 'content' in candidate:
                    content = candidate['content']
                    if 'parts' in content and content['parts']:
                        return content['parts'][0].get('text', '')
        return str(resp)
