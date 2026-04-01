from typing import Dict, Any
from .base import BaseTool
from nlp_enhancements import SentimentAnalyzer

class EmotionTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="EmotionTool",
            description="Detect emotions in user message"
        )
        self.analyzer = SentimentAnalyzer()

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        text = input_data.get("text", "")
        analysis = self.analyzer.analyze(text)
        
        return {
            "emotions": analysis.get("emotions", []),
            "primary_emotion": analysis.get("emotion"),
            "urgency": analysis.get("urgency"),
            "sentiment_score": analysis.get("sentiment_score")
        }
