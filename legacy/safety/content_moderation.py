from typing import Dict, Any

class ContentModeration:
    """
    Stage 1 Safety Component: Checks for illegal or harmful content.
    """
    
    def __init__(self):
        self.blocked_keywords = [
            'how to build a bomb', 'how to make poison', 
            'illegal drugs', 'child porn', 'sex trafficking'
        ]
        # In a real system, this might call an external API like OpenAI Moderation

    def check(self, user_input: str) -> Dict[str, Any]:
        """
        Check input for content violations.
        """
        lower_input = user_input.lower()
        
        for keyword in self.blocked_keywords:
            if keyword in lower_input:
                return {
                    "blocked": True,
                    "reason": "illegal_or_harmful_content",
                    "safe": False
                }
                
        return {
            "blocked": False,
            "safe": True
        }
