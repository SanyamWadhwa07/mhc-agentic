from typing import Dict, Any, List

class OutputSafetyScrubber:
    """
    Stage 2 Post-Processing: Ensures the final response is safe and clean.
    - Removes system internals (e.g., JSON artifacts, debug info).
    - Checks for policy violations.
    - Verifies no prompt leakage.
    """
    
    def __init__(self):
        self.forbidden_terms = [
            "System:", "Controller:", "Tool output:", "JSON:", 
            "You are a therapeutic assistant", "Ignore previous instructions"
        ]

    def scrub(self, response_text: str) -> Dict[str, Any]:
        """
        Scrub the output text.
        """
        clean_text = response_text
        
        # 1. Check for system internals leakage
        for term in self.forbidden_terms:
            if term in clean_text:
                # In a real system, we might regenerate or redact. 
                # Here we'll just log it and attempt to clean or block.
                return {
                    "safe_response": "I apologize, but I encountered an internal error generating the response.",
                    "original_response": response_text,
                    "violation": f"Leaked internal term: {term}",
                    "approved": False
                }
        
        # 2. Basic PII scrubbing (placeholder)
        # clean_text = self._remove_pii(clean_text)
        
        return {
            "safe_response": clean_text,
            "approved": True
        }
