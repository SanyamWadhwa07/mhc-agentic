from typing import Dict, Any
from .base import BaseTool

class InterventionSelectorTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="InterventionSelectorTool",
            description="Recommend therapeutic techniques based on context"
        )

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        situation = input_data.get("situation", "")
        
        # Simple rule-based logic for now, could be LLM-based later
        recommendations = []
        rationale = ""
        
        if "anxiety" in situation or "panic" in situation:
            recommendations.append({"name": "grounding_technique", "priority": "high"})
            recommendations.append({"name": "deep_breathing", "priority": "high"})
            rationale = "Anxiety detected, suggesting grounding and breathing."
        elif "sadness" in situation or "depression" in situation:
            recommendations.append({"name": "behavioral_activation", "priority": "medium"})
            recommendations.append({"name": "validation", "priority": "high"})
            rationale = "Sadness detected, prioritizing validation."
        else:
            recommendations.append({"name": "active_listening", "priority": "high"})
            rationale = "General support situation."
            
        return {
            "recommended_techniques": recommendations,
            "rationale": rationale
        }
