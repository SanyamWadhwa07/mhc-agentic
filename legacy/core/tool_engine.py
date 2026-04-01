from typing import Dict, Any, List
from tools import BaseTool

class ToolExecutionEngine:
    """
    Executes the tool sequence defined by the Controller.
    """
    
    def __init__(self, tool_registry: Dict[str, BaseTool]):
        self.tool_registry = tool_registry

    def execute_plan(self, plan: Dict[str, Any], user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tools in the plan and aggregate results.
        """
        results = {}
        tool_sequence = plan.get("tool_sequence", [])
        
        # 1. Execute intermediate tools
        for step in tool_sequence:
            tool_name = step.get("name")
            tool_input = step.get("input", {})
            
            # Inject text if missing and needed (common for analysis tools)
            if "text" not in tool_input and tool_name in ["EmotionTool", "SentimentTool", "AssessmentTool"]:
                tool_input["text"] = user_input
            
            if tool_name in self.tool_registry:
                tool = self.tool_registry[tool_name]
                try:
                    output = tool.execute(tool_input)
                    results[tool_name] = output
                except Exception as e:
                    results[tool_name] = {"error": str(e)}
            else:
                results[tool_name] = {"error": "Tool not found"}
                
        # 2. Execute Final Action (MasterResponder)
        final_action = plan.get("final_action")
        final_response = None
        
        if final_action == "MasterResponderTool":
            if final_action in self.tool_registry:
                master_tool = self.tool_registry[final_action]
                
                # Build the prompt context for the Master Responder
                # This aggregates all previous tool results
                prompt_context = self._build_master_context(user_input, results, context)
                
                final_response = master_tool.execute({"prompt_context": prompt_context})
        
        return {
            "tool_results": results,
            "final_response": final_response
        }

    def _build_master_context(self, user_input: str, tool_results: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Construct the prompt context for the Master Responder.
        """
        lines = []
        lines.append("=== USER MESSAGE ===")
        lines.append(user_input)
        lines.append("")
        
        lines.append("=== CONTEXT ===")
        lines.append(f"Risk Level: {context.get('risk_level', 'unknown')}")
        lines.append(f"Session Summary: {context.get('session_summary', 'None')}")
        lines.append("")
        
        lines.append("=== TOOL RESULTS ===")
        for tool_name, result in tool_results.items():
            lines.append(f"[{tool_name}]")
            lines.append(str(result))
            lines.append("")
            
        lines.append("=== TASK ===")
        lines.append("Generate a supportive, empathetic response based on the above information.")
        lines.append("Keep it concise (under 150 words).")
        lines.append("Do not be prescriptive or diagnostic.")
        
        return "\n".join(lines)
