"""
Background psychological assessment system.
Seamlessly integrates clinical assessment questions into natural conversation
while tracking responses and generating diagnostic insights.
"""
import json
import os
from typing import Dict, Any, List
from datetime import datetime


class AssessmentTracker:
    """Tracks psychological assessment responses in the background."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.responses = {}
        self.scores = {}
        self.assessment_file = f'sessions/{session_id}_assessment.json'
        
        # PHQ-9 Depression screening
        self.phq9_questions = [
            "little interest or pleasure in doing things",
            "feeling down, depressed, or hopeless",
            "trouble falling or staying asleep, or sleeping too much",
            "feeling tired or having little energy",
            "poor appetite or overeating",
            "feeling bad about yourself or that you are a failure",
            "trouble concentrating on things",
            "moving or speaking slowly or being fidgety or restless",
            "thoughts of being better off dead or hurting yourself"
        ]
        
        # GAD-7 Anxiety screening
        self.gad7_questions = [
            "feeling nervous, anxious, or on edge",
            "not being able to stop or control worrying",
            "worrying too much about different things",
            "trouble relaxing",
            "being so restless that it's hard to sit still",
            "becoming easily annoyed or irritable",
            "feeling afraid as if something awful might happen"
        ]
        
        # Keywords for automatic detection
        self.symptom_keywords = {
            'depression': ['sad', 'down', 'depressed', 'hopeless', 'worthless', 'empty', 'numb'],
            'anxiety': ['anxious', 'worried', 'nervous', 'panic', 'fear', 'scared', 'tense'],
            'sleep': ['sleep', 'insomnia', 'tired', 'exhausted', 'fatigue', 'rest'],
            'appetite': ['appetite', 'eating', 'food', 'hungry', 'weight'],
            'concentration': ['focus', 'concentrate', 'attention', 'distracted', 'memory'],
            'energy': ['energy', 'motivation', 'tired', 'exhausted', 'fatigue'],
            'irritability': ['irritable', 'angry', 'annoyed', 'frustrated'],
            'suicidal': ['suicide', 'kill myself', 'end my life', 'better off dead', 'harm myself']
        }
        
        self._load_assessment()
    
    def analyze_message(self, user_message: str) -> Dict[str, Any]:
        """Analyze user message for assessment indicators."""
        message_lower = user_message.lower()
        detected = {
            'symptoms': [],
            'severity_indicators': [],
            'assessment_relevance': {}
        }
        
        # Detect symptoms
        for symptom, keywords in self.symptom_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected['symptoms'].append(symptom)
                self._record_symptom(symptom, user_message)
        
        # Check PHQ-9 indicators
        for i, question_text in enumerate(self.phq9_questions):
            keywords = question_text.split()[:3]  # First 3 words as keywords
            if any(kw in message_lower for kw in keywords):
                detected['assessment_relevance'][f'phq9_{i}'] = True
        
        # Check GAD-7 indicators
        for i, question_text in enumerate(self.gad7_questions):
            keywords = question_text.split()[:3]
            if any(kw in message_lower for kw in keywords):
                detected['assessment_relevance'][f'gad7_{i}'] = True
        
        # Severity indicators
        if any(word in message_lower for word in ['very', 'extremely', 'always', 'constantly', 'severe']):
            detected['severity_indicators'].append('high_frequency')
        if any(word in message_lower for word in ['every day', 'all the time', 'never stops']):
            detected['severity_indicators'].append('persistent')
        
        return detected
    
    def _record_symptom(self, symptom: str, context: str):
        """Record symptom mention with context."""
        if symptom not in self.responses:
            self.responses[symptom] = []
        
        self.responses[symptom].append({
            'timestamp': datetime.now().isoformat(),
            'context': context[:200],  # Store snippet
            'detected': True
        })
        
        self._save_assessment()
    
    def calculate_scores(self) -> Dict[str, Any]:
        """Calculate assessment scores based on detected symptoms."""
        scores = {
            'phq9_estimated': 0,
            'gad7_estimated': 0,
            'risk_level': 'unknown',
            'concerns': []
        }
        
        # Estimate PHQ-9 score based on symptom mentions
        depression_symptoms = ['depression', 'sleep', 'energy', 'appetite', 'concentration']
        phq9_count = sum(1 for s in depression_symptoms if s in self.responses)
        scores['phq9_estimated'] = min(phq9_count * 2, 27)  # Rough estimate
        
        # Estimate GAD-7 score
        anxiety_symptoms = ['anxiety', 'worry', 'nervous', 'restless', 'irritability']
        gad7_count = sum(1 for s in ['anxiety', 'irritability'] if s in self.responses)
        scores['gad7_estimated'] = min(gad7_count * 3, 21)
        
        # Risk assessment
        if 'suicidal' in self.responses:
            scores['risk_level'] = 'high'
            scores['concerns'].append('Suicidal ideation detected - immediate intervention needed')
        elif scores['phq9_estimated'] >= 15:
            scores['risk_level'] = 'moderate-high'
            scores['concerns'].append('Significant depression symptoms')
        elif scores['gad7_estimated'] >= 10:
            scores['risk_level'] = 'moderate'
            scores['concerns'].append('Significant anxiety symptoms')
        else:
            scores['risk_level'] = 'low-moderate'
        
        # Additional insights
        if len(self.responses) >= 3:
            scores['concerns'].append(f'{len(self.responses)} different symptom areas identified')
        
        self.scores = scores
        self._save_assessment()
        return scores
    
    def get_assessment_summary(self) -> str:
        """Get natural language assessment summary."""
        if not self.responses:
            return "No significant mental health concerns detected yet."
        
        scores = self.calculate_scores()
        
        summary_parts = []
        summary_parts.append(f"Risk Level: {scores['risk_level'].upper()}")
        
        if self.responses:
            symptoms = ', '.join(self.responses.keys())
            summary_parts.append(f"Symptoms discussed: {symptoms}")
        
        if scores['concerns']:
            summary_parts.append("Key concerns: " + '; '.join(scores['concerns']))
        
        return ' | '.join(summary_parts)
    
    def get_background_context(self) -> str:
        """Get gentle, non-diagnostic context for LLM (invisible to user)."""
        if not self.responses:
            return ""
        
        scores = self.calculate_scores()
        
        # Use soft, exploratory language instead of clinical labels
        gentle_observations = []
        
        if scores['phq9_estimated'] >= 10:
            gentle_observations.append("user mentioned feeling down or low mood")
        elif scores['phq9_estimated'] >= 5:
            gentle_observations.append("user expressed some sadness")
        
        if scores['gad7_estimated'] >= 10:
            gentle_observations.append("user described worry or tension")
        elif scores['gad7_estimated'] >= 5:
            gentle_observations.append("user mentioned some anxious feelings")
        
        if not gentle_observations:
            return ""
        
        context = f"""[BACKGROUND OBSERVATIONS - Gentle, non-diagnostic language only]
What user shared: {', '.join(self.responses.keys())}
Observations: {', '.join(gentle_observations)}
Risk Level: {scores['risk_level']}

IMPORTANT:
- DO NOT use clinical terms: "depression", "anxiety", "dissociation", "repression", "PTSD"
- DO NOT diagnose or label
- USE instead: "feeling down", "worried", "going through tough time", "sometimes numb"
- If exploring these: use soft language like "Sometimes people feel numb after hurt. Does that fit for you?"
[Continue natural, human conversation with this gentle awareness]
"""
        return context
        return context
    
    def _save_assessment(self):
        """Save assessment data to disk."""
        assessment_data = {
            'session_id': self.session_id,
            'responses': self.responses,
            'scores': self.scores,
            'last_updated': datetime.now().isoformat()
        }
        
        os.makedirs('sessions', exist_ok=True)
        with open(self.assessment_file, 'w', encoding='utf-8') as f:
            json.dump(assessment_data, f, indent=2, ensure_ascii=False)
    
    def _load_assessment(self):
        """Load existing assessment data."""
        if os.path.exists(self.assessment_file):
            with open(self.assessment_file, 'r', encoding='utf-8') as f:
                assessment_data = json.load(f)
                self.responses = assessment_data.get('responses', {})
                self.scores = assessment_data.get('scores', {})
