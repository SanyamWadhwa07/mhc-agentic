from typing import Dict, Any
from .base import BaseTool
from nlp_enhancements import SentimentAnalyzer

class SentimentTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="SentimentTool",
            description="Analyze sentiment polarity and score"
        )
        self.analyzer = SentimentAnalyzer()

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        text = input_data.get("text", "")
        analysis = self.analyzer.analyze(text)
        
        score = analysis.get("sentiment_score", 0)
        if score > 0.2:
            sentiment = "positive"
        elif score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"
            
        return {
            "sentiment": sentiment,
            "score": score
        }
