from typing import Dict, Any
from .base import BaseTool
from nlp_enhancements import ConversationInsights

class PatternDetectorTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="PatternDetectorTool",
            description="Identify conversation patterns and loops"
        )
        self.insights = ConversationInsights()

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # This tool expects a list of messages to analyze
        # In a real flow, the controller might pass the history or we fetch it
        messages = input_data.get("messages", [])
        
        patterns = self.insights.detect_patterns(messages)
        topics = self.insights.extract_topics(messages)
        
        return {
            "patterns": patterns,
            "topics": list(topics.keys())
        }
