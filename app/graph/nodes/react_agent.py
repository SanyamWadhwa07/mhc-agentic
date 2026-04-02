import json
import structlog
from app.config import settings
from app.services.llm_service import LLMService
from app.prompts.react_prompt import build_react_prompt
from app.tools.therapy_tool import TherapyTool
from app.tools.assessment_tool import AssessmentTool
from app.tools.resource_tool import ResourceTool
from app.tools.memory_read_tool import MemoryReadTool
from app.tools.risk_evaluator import RiskEvaluator

log = structlog.get_logger()
llm = LLMService()

TOOLS = {
    "TherapyTool": TherapyTool(),
    "AssessmentTool": AssessmentTool(),
    "ResourceTool": ResourceTool(),
    "MemoryReadTool": MemoryReadTool(),
    "RiskEvaluator": RiskEvaluator(),
}

TOOL_SCHEMAS = {
    "TherapyTool": {"query": str},
    "AssessmentTool": {"query": str},
    "ResourceTool": {"query": str},
    "MemoryReadTool": {"user_id": str},
    "RiskEvaluator": {"conversation": list},
}


def validate_tool_schema(action: dict) -> bool:
    tool_name = action.get("tool")
    if tool_name not in TOOL_SCHEMAS:
        return False
    schema = TOOL_SCHEMAS[tool_name]
    args = action.get("args", {})
    return all(k in args for k in schema)


async def react_agent_node(state):
    message = state["sanitized_message"]
    history = state.get("session_history", [])[-5:]
    tool_results = []
    steps = 0

    summary = state.get("session_summary") or ""
    context = {"message": message, "history": history, "tool_results": tool_results}

    while steps < settings.react_max_steps:
        steps += 1
        prompt = build_react_prompt(context, summary=summary)

        try:
            raw, _ = await llm.call(
                model=settings.groq_fast_model,  # 8B for reasoning
                messages=prompt,
                response_format={"type": "json_object"}
            )
            action = json.loads(raw)
        except Exception as e:
            log.error("react_parse_error", step=steps, error=str(e))
            break

        if action.get("done"):
            break

        # Schema validation
        if not validate_tool_schema(action):
            log.warning("invalid_tool_schema", step=steps, action=action)
            # Retry once
            try:
                raw, _ = await llm.call(
                    model=settings.groq_fast_model,
                    messages=prompt,
                    response_format={"type": "json_object"}
                )
                action = json.loads(raw)
                if not validate_tool_schema(action):
                    log.error("react_invalid_schema_retry_failed", step=steps)
                    break
            except Exception:
                break

        # Execute tool
        tool_name = action["tool"]
        tool_args = action.get("args", {})

        try:
            tool = TOOLS[tool_name]
            observation = await tool.run(**tool_args)
            tool_results.append({"tool": tool_name, "args": tool_args, "result": observation})
            context["tool_results"] = tool_results
        except Exception as e:
            log.error("tool_execution_error", tool=tool_name, error=str(e))
            tool_results.append({"tool": tool_name, "error": str(e)})

    return {**state, "react_steps": steps, "tool_results": tool_results}
