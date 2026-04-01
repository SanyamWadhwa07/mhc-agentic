from typing import Dict, List, Any

class ImmediateCrisisDetector:
    """
    Stage 1 Safety Component: Detects immediate crisis situations.
    Checks for suicidal ideation, self-harm intent, and violence threats.
    """
    
    def __init__(self):
        self.crisis_keywords = [
            'suicide', 'kill myself', 'end my life', 'harm myself', 
            'want to die', 'self-harm', 'cutting', 'overdose', 
            'can\'t go on', 'better off dead', 'hang myself',
            'shoot myself', 'jump off', 'end it all'
        ]
        self.violence_keywords = [
            'kill them', 'hurt them', 'shoot them', 'murder',
            'bomb', 'attack', 'stab'
        ]

    def check(self, user_input: str) -> Dict[str, Any]:
        """
        Check input for crisis signals.
        Returns a dict with risk_level and details.
        """
        lower_input = user_input.lower()
        
        # Check for self-harm/suicide
        for keyword in self.crisis_keywords:
            if keyword in lower_input:
                return {
                    "risk_level": "high",
                    "crisis_type": "self_harm",
                    "trigger_word": keyword,
                    "safe": False
                }
                
        # Check for violence
        for keyword in self.violence_keywords:
            if keyword in lower_input:
                return {
                    "risk_level": "high",
                    "crisis_type": "violence",
                    "trigger_word": keyword,
                    "safe": False
                }
                
        return {
            "risk_level": "none",
            "safe": True
        }
