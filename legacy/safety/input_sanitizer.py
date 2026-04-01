import re
from typing import Dict, Any

class InputSanitizer:
    """
    Stage 1 Safety Component: Sanitizes input to prevent injection and normalize text.
    """
    
    def sanitize(self, user_input: str) -> Dict[str, Any]:
        """
        Sanitize the user input.
        """
        # 1. Remove potential system directives (basic protection)
        # Remove lines starting with "System:", "Instruction:", etc. if they look like prompt injection
        clean_text = re.sub(r'^(System|Instruction|Ignore previous instructions):.*$', '', user_input, flags=re.MULTILINE | re.IGNORECASE)
        
        # 2. Basic whitespace normalization
        clean_text = " ".join(clean_text.split())
        
        # 3. Escape special characters if needed (for JSON safety, though json.dumps handles this)
        # Here we just ensure it's a string
        
        return {
            "safe_input": clean_text,
            "original_input": user_input,
            "was_modified": clean_text != user_input
        }
