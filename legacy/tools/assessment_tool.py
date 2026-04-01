from typing import Dict, Any
from .base import BaseTool
from assessment_tracker import AssessmentTracker

class AssessmentTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="AssessmentTool",
            description="Run PHQ-9/GAD-7 or other validated assessments"
        )
        # In a real app, we'd need session_id to init tracker
        self.tracker = AssessmentTracker("temp_session")

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        text = input_data.get("text", "")
        analysis = self.tracker.analyze_message(text)
        
        return {
            "symptoms": analysis.get("symptoms", []),
            "severity_indicators": analysis.get("severity_indicators", []),
            "assessment_relevance": analysis.get("assessment_relevance", [])
        }
