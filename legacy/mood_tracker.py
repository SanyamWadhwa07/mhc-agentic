"""
Mood tracking agent that maintains emotional state history and adapts responses accordingly.
Tracks sentiment trends, emotional patterns, and provides mood-aware context for response generation.
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any
from collections import deque


class MoodTracker:
    """Tracks user's mood, sentiment, and emotional state across conversation."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.mood_history = deque(maxlen=20)  # Keep last 20 mood points
        self.session_file = f'sessions/{session_id}_mood.json'
        self._load_mood_data()
        
    def _load_mood_data(self):
        """Load existing mood tracking data."""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self.mood_history = deque(data.get('mood_history', []), maxlen=20)
            except:
                pass
    
    def _save_mood_data(self):
        """Persist mood tracking data."""
        os.makedirs('sessions', exist_ok=True)
        with open(self.session_file, 'w') as f:
            json.dump({
                'session_id': self.session_id,
                'mood_history': list(self.mood_history),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def record_mood(self, sentiment_data: Dict, user_message: str):
        """Record mood point from sentiment analysis."""
        mood_point = {
            'timestamp': datetime.now().isoformat(),
            'emotion': sentiment_data.get('emotion', 'neutral'),
            'sentiment_score': sentiment_data.get('sentiment_score', 0.0),
            'urgency': sentiment_data.get('urgency', 'low'),
            'crisis_detected': sentiment_data.get('crisis_detected', False),
            'message_length': len(user_message.split()),
            'message_sample': user_message[:50]  # First 50 chars for context
        }
        self.mood_history.append(mood_point)
        self._save_mood_data()
    
    def get_mood_trend(self) -> str:
        """Analyze recent mood trend."""
        if len(self.mood_history) < 3:
            return "establishing_baseline"
        
        recent_scores = [m['sentiment_score'] for m in list(self.mood_history)[-5:]]
        
        # Calculate trend
        if len(recent_scores) >= 3:
            early_avg = sum(recent_scores[:2]) / 2
            late_avg = sum(recent_scores[-2:]) / 2
            
            if late_avg > early_avg + 0.15:
                return "improving"
            elif late_avg < early_avg - 0.15:
                return "declining"
        
        return "stable"
    
    def get_emotional_pattern(self) -> Dict[str, int]:
        """Get frequency of emotions in recent history."""
        if not self.mood_history:
            return {}
        
        emotion_counts = {}
        for mood in self.mood_history:
            emotion = mood['emotion']
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        return dict(sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True))
    
    def get_current_state(self) -> str:
        """Get current emotional state description."""
        if not self.mood_history:
            return "neutral"
        
        latest = self.mood_history[-1]
        return latest['emotion']
    
    def get_urgency_level(self) -> str:
        """Get current urgency level."""
        if not self.mood_history:
            return "low"
        
        latest = self.mood_history[-1]
        return latest['urgency']
    
    def is_crisis_state(self) -> bool:
        """Check if user is in crisis state."""
        if not self.mood_history:
            return False
        
        # Check last 3 messages for crisis indicators
        recent = list(self.mood_history)[-3:]
        return any(m.get('crisis_detected', False) for m in recent)
    
    def get_response_guidance(self) -> Dict[str, Any]:
        """Generate guidance for response adaptation based on mood tracking."""
        if not self.mood_history:
            return {
                'tone': 'warm and welcoming',
                'approach': 'open and curious',
                'priority': 'build rapport'
            }
        
        current_emotion = self.get_current_state()
        trend = self.get_mood_trend()
        urgency = self.get_urgency_level()
        pattern = self.get_emotional_pattern()
        
        # Determine response guidance based on mood data
        guidance = {
            'current_emotion': current_emotion,
            'trend': trend,
            'urgency': urgency,
            'dominant_emotions': list(pattern.keys())[:3] if pattern else [],
            'tone': self._determine_tone(current_emotion, urgency),
            'approach': self._determine_approach(trend, current_emotion),
            'priority': self._determine_priority(urgency, current_emotion),
            'caution': self._determine_caution(current_emotion, trend)
        }
        
        return guidance
    
    def _determine_tone(self, emotion: str, urgency: str) -> str:
        """Determine appropriate tone based on emotion and urgency."""
        if urgency in ['critical', 'high']:
            return 'calm, grounded, direct'
        
        tone_map = {
            'crisis': 'calm and immediate',
            'distressed': 'gentle and steady',
            'struggling': 'warm and supportive',
            'coping': 'encouraging and affirming',
            'neutral': 'natural and conversational'
        }
        return tone_map.get(emotion, 'warm and present')
    
    def _determine_approach(self, trend: str, emotion: str) -> str:
        """Determine conversation approach based on trend."""
        if trend == 'improving':
            return 'acknowledge progress, reinforce what\'s working'
        elif trend == 'declining':
            return 'check in gently, explore what changed'
        elif emotion in ['crisis', 'distressed']:
            return 'stay present, focus on safety and grounding'
        else:
            return 'continue exploring with curiosity'
    
    def _determine_priority(self, urgency: str, emotion: str) -> str:
        """Determine response priority."""
        if urgency == 'critical' or emotion == 'crisis':
            return 'immediate safety and crisis resources'
        elif urgency == 'high':
            return 'emotional stabilization and support'
        elif emotion == 'struggling':
            return 'validation and gentle exploration'
        else:
            return 'understanding and connection'
    
    def _determine_caution(self, emotion: str, trend: str) -> str:
        """Determine any cautions for response generation."""
        cautions = []
        
        if emotion in ['crisis', 'distressed']:
            cautions.append('Avoid overwhelming with questions')
        
        if trend == 'declining':
            cautions.append('Watch for worsening - may need more support')
        
        if emotion == 'struggling' and trend == 'stable':
            cautions.append('User may be stuck - consider gentle shift in approach')
        
        return ' | '.join(cautions) if cautions else 'none'
    
    def get_mood_summary(self) -> str:
        """Get human-readable mood summary for context."""
        if not self.mood_history:
            return "No mood history yet."
        
        guidance = self.get_response_guidance()
        pattern = self.get_emotional_pattern()
        
        summary_parts = []
        summary_parts.append(f"Current state: {guidance['current_emotion']}")
        summary_parts.append(f"Trend: {guidance['trend']}")
        
        if pattern:
            top_emotions = ', '.join([f"{e} ({c}x)" for e, c in list(pattern.items())[:3]])
            summary_parts.append(f"Recent emotions: {top_emotions}")
        
        summary_parts.append(f"Response approach: {guidance['approach']}")
        
        if guidance['caution'] != 'none':
            summary_parts.append(f"⚠️ {guidance['caution']}")
        
        return '\n'.join(summary_parts)
