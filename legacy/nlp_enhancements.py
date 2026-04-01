"""
Advanced NLP enhancements for natural conversation and sentiment analysis.
"""
import re
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple
from collections import Counter


class SentimentAnalyzer:
    """Real-time sentiment and emotion detection from user messages."""
    
    def __init__(self):
        # Multi-label emotion lexicons (10 categories)
        self.emotion_lexicons = {
            'hurt': {'hurt', 'hurts', 'wounded', 'pain', 'aching', 'stung', 'cut deep', 'crushed', 'painful'},
            'sadness': {'sad', 'depressed', 'down', 'blue', 'miserable', 'unhappy', 'tearful', 'crying', 'cry'},
            'betrayal': {'betrayed', 'lied', 'lied to', 'deceived', 'cheated', 'backstabbed', 'used', 'manipulated', 'trust broken', 'promised'},
            'anger': {'angry', 'mad', 'furious', 'pissed', 'rage', 'frustrated', 'irritated', 'outraged'},
            'shame': {'ashamed', 'embarrassed', 'humiliated', 'guilty', 'dirty', 'worthless', 'pathetic', 'disgusted with myself', 'stupid', 'idiot', 'dumb', 'fool'},
            'fear': {'scared', 'afraid', 'terrified', 'anxious', 'panic', 'worried', 'nervous', 'frightened'},
            'loneliness': {'lonely', 'alone', 'isolated', 'abandoned', 'disconnected', 'nobody cares', 'invisible', 'no one'},
            'confusion': {'confused', 'lost', 'dont understand', 'mixed up', 'unclear', 'bewildered'},
            'grief': {'grief', 'loss', 'mourning', 'miss', 'gone', 'died', 'death', 'lost someone', 'passed away'},
            'hopelessness': {'hopeless', 'no point', 'give up', 'cant go on', 'why bother', 'nothing matters', 'pointless', 'alive or dead', 'doesnt matter'}
        }
        
        # Basic sentiment words
        self.positive_words = {
            'happy', 'joy', 'excited', 'grateful', 'hopeful', 'proud', 'peaceful',
            'calm', 'relaxed', 'confident', 'motivated', 'better', 'good', 'great'
        }
        self.negative_words = {
            'sad', 'depressed', 'anxious', 'worried', 'scared', 'angry', 'frustrated',
            'hopeless', 'worthless', 'tired', 'exhausted', 'overwhelmed', 'stuck', 'alone'
        }
        self.crisis_words = {
            'suicide', 'kill', 'die', 'end it', 'hurt myself', 'self-harm', 'cutting',
            'overdose', 'give up', 'no point', 'better off dead'
        }
        
    def analyze(self, text: str) -> Dict:
        """Analyze sentiment, emotion, and urgency with multi-label emotion detection."""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        # Multi-label emotion detection
        detected_emotions = []
        for emotion_label, emotion_words in self.emotion_lexicons.items():
            # Check both individual words and phrases
            if words & emotion_words or any(phrase in text_lower for phrase in emotion_words if ' ' in phrase):
                detected_emotions.append(emotion_label)
        
        # Graded crisis detection
        high_crisis_words = {'kill myself', 'end my life', 'suicide', 'suicidal', 'better off dead'}
        soft_crisis_words = {'hopeless', 'no point', 'give up', 'cant go on'}
        
        # Check for high crisis phrases (multi-word)
        high_crisis_detected = any(phrase in text_lower for phrase in high_crisis_words)
        soft_crisis_detected = bool(words & soft_crisis_words)
        
        # Context-based sentiment scoring
        positive_count = len(words & self.positive_words)
        negative_count = len(words & self.negative_words)
        
        # Boost negative score if strong negative emotions detected
        if 'betrayal' in detected_emotions or 'shame' in detected_emotions:
            negative_count += 2
        if 'hurt' in detected_emotions or 'anger' in detected_emotions:
            negative_count += 1
        
        # Calculate sentiment score (-1 to 1)
        total = positive_count + negative_count
        if total > 0:
            sentiment_score = (positive_count - negative_count) / total
        else:
            # If no explicit sentiment words, infer from emotions
            if detected_emotions:
                sentiment_score = -0.5  # Assume negative if expressing emotions
            else:
                sentiment_score = 0.0
            
        # Determine primary emotion with graded crisis response
        if high_crisis_detected:
            primary_emotion = "crisis"
            urgency = "critical"
            crisis_detected = True
        elif soft_crisis_detected or 'hopelessness' in detected_emotions:
            primary_emotion = "distressed"
            urgency = "high"
            crisis_detected = False
        elif 'anger' in detected_emotions and len(detected_emotions) > 1:
            primary_emotion = "distressed"
            urgency = "high"
            crisis_detected = False
        elif detected_emotions:
            # Use most contextually severe emotion
            severity_order = ['betrayal', 'shame', 'grief', 'hurt', 'loneliness', 'sadness', 'anger', 'fear', 'confusion']
            for emotion in severity_order:
                if emotion in detected_emotions:
                    primary_emotion = emotion
                    break
            else:
                primary_emotion = detected_emotions[0]
            
            urgency = "moderate" if len(detected_emotions) > 2 else "low"
            crisis_detected = False
        elif negative_count > positive_count * 2:
            primary_emotion = "struggling"
            urgency = "moderate"
            crisis_detected = False
        elif positive_count > negative_count:
            primary_emotion = "coping"
            urgency = "low"
            crisis_detected = False
        else:
            primary_emotion = "neutral"
            urgency = "low"
            crisis_detected = False
            
        return {
            "sentiment_score": round(sentiment_score, 2),
            "emotion": primary_emotion,
            "emotions": detected_emotions,  # All detected emotions
            "urgency": urgency,
            "crisis_detected": crisis_detected,
            "positive_indicators": positive_count,
            "negative_indicators": negative_count
        }


class ConversationInsights:
    """Extract insights and patterns from conversation history."""
    
    def __init__(self):
        self.topic_keywords = {
            'sleep': ['sleep', 'insomnia', 'tired', 'exhausted', 'rest', 'wake'],
            'work_stress': ['work', 'job', 'boss', 'deadline', 'pressure', 'career'],
            'relationships': ['partner', 'spouse', 'family', 'friend', 'relationship', 'lonely'],
            'self_worth': ['worthless', 'failure', 'stupid', 'useless', 'inadequate'],
            'anxiety': ['anxious', 'panic', 'worry', 'nervous', 'fear', 'scared'],
            'depression': ['depressed', 'sad', 'hopeless', 'empty', 'numb'],
            'coping': ['exercise', 'meditation', 'therapy', 'breathing', 'journaling']
        }
        
    def extract_topics(self, messages: List[Dict]) -> Dict[str, int]:
        """Identify recurring topics across conversation."""
        topic_counts = Counter()
        
        for msg in messages:
            if msg.get('role') == 'User':
                text_lower = msg.get('content', '').lower()
                words = set(re.findall(r'\b\w+\b', text_lower))
                
                for topic, keywords in self.topic_keywords.items():
                    if words & set(keywords):
                        topic_counts[topic] += 1
                        
        return dict(topic_counts.most_common(5))
    
    def detect_patterns(self, messages: List[Dict]) -> Dict:
        """Detect behavioral patterns and conversation trends."""
        if len(messages) < 4:
            return {}
            
        # Analyze recent sentiment trend
        recent_sentiments = []
        analyzer = SentimentAnalyzer()
        
        for msg in messages[-6:]:
            if msg.get('role') == 'User':
                sentiment = analyzer.analyze(msg.get('content', ''))
                recent_sentiments.append(sentiment['sentiment_score'])
        
        if len(recent_sentiments) >= 2:
            trend = "improving" if recent_sentiments[-1] > recent_sentiments[0] else "declining"
        else:
            trend = "stable"
            
        # Check engagement
        user_msgs = [m for m in messages if m.get('role') == 'User']
        avg_length = sum(len(m.get('content', '')) for m in user_msgs) / len(user_msgs) if user_msgs else 0
        
        engagement = "high" if avg_length > 100 else "moderate" if avg_length > 30 else "low"
        
        return {
            "sentiment_trend": trend,
            "engagement_level": engagement,
            "conversation_depth": len(messages),
            "topics_discussed": len(self.extract_topics(messages))
        }


class ResponsePersonalizer:
    """Personalize responses based on user history and preferences."""
    
    def __init__(self):
        self.user_profiles = {}
        
    def update_profile(self, session_id: str, insights: Dict):
        """Update user profile with conversation insights."""
        if session_id not in self.user_profiles:
            self.user_profiles[session_id] = {
                "created_at": datetime.now().isoformat(),
                "preferred_topics": [],
                "engagement_patterns": [],
                "sentiment_history": []
            }
            
        profile = self.user_profiles[session_id]
        profile["last_updated"] = datetime.now().isoformat()
        profile["sentiment_history"].append(insights.get("sentiment_score", 0))
        
        # Keep last 20 sentiment scores
        profile["sentiment_history"] = profile["sentiment_history"][-20:]
        
    def get_personalization_context(self, session_id: str) -> str:
        """Generate context for personalizing responses."""
        if session_id not in self.user_profiles:
            return ""
            
        profile = self.user_profiles[session_id]
        sentiment_avg = sum(profile["sentiment_history"]) / len(profile["sentiment_history"]) if profile["sentiment_history"] else 0
        
        if sentiment_avg < -0.3:
            return "User has been experiencing persistent negative emotions. Be extra supportive and gentle."
        elif sentiment_avg > 0.3:
            return "User shows positive coping. Encourage and reinforce their progress."
        else:
            return "User emotions are mixed. Validate their experience and explore both challenges and strengths."


class LearningSystem:
    """Continuous learning from conversation patterns and outcomes."""
    
    def __init__(self, learning_file: str = "sessions/learning_data.json"):
        self.learning_file = learning_file
        self.learning_data = self._load_learning_data()
        
    def _load_learning_data(self) -> Dict:
        """Load existing learning data."""
        try:
            with open(self.learning_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "successful_interventions": [],
                "common_topics": {},
                "effective_responses": [],
                "crisis_patterns": [],
                "user_preferences": {}
            }
    
    def _save_learning_data(self):
        """Persist learning data."""
        os.makedirs(os.path.dirname(self.learning_file), exist_ok=True)
        with open(self.learning_file, 'w') as f:
            json.dump(self.learning_data, f, indent=2)
    
    def record_successful_interaction(self, context: Dict):
        """Record what worked well for future reference."""
        # Extract emotion properly - could be in 'sentiment' or 'emotion' key
        emotion = context.get("emotion") or context.get("sentiment")
        
        # Determine intervention type from agents used
        agents = context.get("agents_used", [])
        if agents:
            intervention_type = f"{'+'.join(agents)} approach"
        else:
            intervention_type = "general support"
        
        self.learning_data["successful_interventions"].append({
            "timestamp": datetime.now().isoformat(),
            "user_emotion": emotion,
            "topics": context.get("topics", []),
            "intervention_type": intervention_type,
            "agents_used": agents,
            "outcome": "positive",
            "user_input_sample": context.get("user_input", "")[:100]  # First 100 chars
        })
        
        # Update common topics
        for topic in context.get("topics", []):
            self.learning_data["common_topics"][topic] = self.learning_data["common_topics"].get(topic, 0) + 1
        
        # Keep last 100 interactions
        self.learning_data["successful_interventions"] = self.learning_data["successful_interventions"][-100:]
        self._save_learning_data()
    
    def get_best_practices(self, emotion: str, topics: List[str]) -> str:
        """Retrieve learned best practices for similar situations."""
        relevant = [
            i for i in self.learning_data["successful_interventions"]
            if i.get("user_emotion") == emotion or any(t in i.get("topics", []) for t in topics)
        ]
        
        if not relevant:
            return ""
        
        # Get most common successful intervention types
        interventions = Counter(i.get("intervention_type") for i in relevant if i.get("intervention_type"))
        
        if not interventions:
            return ""
        
        # Build recommendations from top 2 most effective approaches
        recommendations = []
        for intervention, count in interventions.most_common(2):
            recommendations.append(f"✓ {intervention} (worked {count} times)")
        
        if recommendations:
            return f"What has worked before: {', '.join(recommendations)}"
        return ""


class ConversationalContext:
    """Enhanced context management with NLP insights."""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.insights_extractor = ConversationInsights()
        self.personalizer = ResponsePersonalizer()
        self.learning_system = LearningSystem()
        
    def analyze_message(self, session_id: str, user_message: str, conversation_history: List[Dict]) -> Dict:
        """Comprehensive analysis of user message with all NLP enhancements."""
        # Sentiment analysis
        sentiment = self.sentiment_analyzer.analyze(user_message)
        
        # Conversation insights
        topics = self.insights_extractor.extract_topics(conversation_history)
        patterns = self.insights_extractor.detect_patterns(conversation_history)
        
        # Personalization
        self.personalizer.update_profile(session_id, sentiment)
        personalization_ctx = self.personalizer.get_personalization_context(session_id)
        
        # Learning-based recommendations
        best_practices = self.learning_system.get_best_practices(
            sentiment.get("emotion", "neutral"),
            list(topics.keys())
        )
        
        return {
            "sentiment": sentiment,
            "topics": list(topics.keys()) if topics else [],
            "patterns": list(patterns.keys()) if patterns else [],
            "personalization": {
                "context": personalization_ctx,
                "preferred_tone": self._infer_tone(sentiment),
                "effective_techniques": self._get_effective_techniques(session_id)
            },
            "learned_recommendations": best_practices.split('\n') if best_practices else [],
            "enhanced_context": self._build_enhanced_context(sentiment, topics, patterns, personalization_ctx, best_practices)
        }
    
    def _build_enhanced_context(self, sentiment: Dict, topics: Dict, patterns: Dict, 
                                personalization: str, best_practices: str) -> str:
        """Build rich context for LLM."""
        context_parts = []
        
        if sentiment.get("crisis_detected"):
            context_parts.append("⚠️ CRISIS INDICATORS DETECTED - Prioritize safety")
            
        if sentiment.get("urgency") in ["high", "critical"]:
            context_parts.append(f"User urgency level: {sentiment['urgency']}")
            
        context_parts.append(f"User emotional state: {sentiment.get('emotion', 'neutral')}")
        
        if topics:
            context_parts.append(f"Main topics: {', '.join(topics.keys())}")
            
        if patterns.get("sentiment_trend"):
            context_parts.append(f"Sentiment trend: {patterns['sentiment_trend']}")
            
        if personalization:
            context_parts.append(personalization)
            
        if best_practices:
            context_parts.append(best_practices)
            
        return "\n".join(context_parts)
    
    def _infer_tone(self, sentiment: Dict) -> str:
        """Infer preferred communication tone from sentiment."""
        emotion = sentiment.get('emotion', 'neutral')
        if emotion in ['crisis', 'distressed']:
            return 'direct and supportive'
        elif emotion == 'struggling':
            return 'gentle and encouraging'
        else:
            return 'warm and conversational'
    
    def _get_effective_techniques(self, session_id: str) -> List[str]:
        """Get techniques that have worked for this user."""
        # Placeholder - can be expanded based on learning system
        return []
    
    def record_success(self, session_id: str, user_input: str, response: str, 
                      sentiment: Dict, topics: List[str], agents_used: List[str]):
        """Record successful interaction for learning."""
        interaction_context = {
            "session_id": session_id,
            "user_input": user_input,
            "response": response,
            "sentiment": sentiment.get('emotion', 'neutral'),
            "topics": topics,
            "agents_used": agents_used,
            "timestamp": datetime.now().isoformat()
        }
        self.learning_system.record_successful_interaction(interaction_context)
