from langgraph.graph import StateGraph, END
from app.graph.state import MHCState
from app.graph.nodes.rate_limiter import rate_limiter_node
from app.graph.nodes.safety_gate import safety_gate_node
from app.graph.nodes.emotional_scorer import emotional_scorer_node
from app.graph.nodes.path_classifier import path_classifier_node
from app.graph.nodes.direct_responder import direct_responder_node
from app.graph.nodes.react_agent import react_agent_node
from app.graph.nodes.rag_confidence import rag_confidence_node
from app.graph.nodes.model_router import model_router_node
from app.graph.nodes.response_validator import response_validator_node
from app.graph.nodes.output_normalizer import output_normalizer_node
from app.graph.nodes.observability import observability_node
from app.graph.nodes.memory_update import memory_update_node


def route_after_rate_limiter(state):
    if state.get("is_rate_limited"):
        return "end"
    return "safety_gate"


def route_after_safety(state):
    if state.get("is_crisis"):
        return "end"
    return "emotional_scorer"


def route_after_classifier(state):
    path = state.get("path", "complex")
    if path == "simple":
        return "model_router"
    return "react_agent"


def build_graph():
    graph = StateGraph(MHCState)

    graph.add_node("rate_limiter", rate_limiter_node)
    graph.add_node("safety_gate", safety_gate_node)
    graph.add_node("emotional_scorer", emotional_scorer_node)
    graph.add_node("path_classifier", path_classifier_node)
    graph.add_node("model_router", model_router_node)
    graph.add_node("direct_responder", direct_responder_node)
    graph.add_node("react_agent", react_agent_node)
    graph.add_node("rag_confidence", rag_confidence_node)
    graph.add_node("response_validator", response_validator_node)
    graph.add_node("output_normalizer", output_normalizer_node)
    graph.add_node("observability", observability_node)
    graph.add_node("memory_update", memory_update_node)

    graph.set_entry_point("rate_limiter")

    graph.add_conditional_edges("rate_limiter", route_after_rate_limiter, {
        "end": END,
        "safety_gate": "safety_gate"
    })

    graph.add_conditional_edges("safety_gate", route_after_safety, {
        "end": END,
        "emotional_scorer": "emotional_scorer"
    })

    graph.add_edge("emotional_scorer", "path_classifier")

    graph.add_conditional_edges("path_classifier", route_after_classifier, {
        "model_router": "model_router",
        "react_agent": "react_agent"
    })

    # Simple path
    graph.add_edge("model_router", "direct_responder")
    graph.add_edge("direct_responder", "response_validator")

    # Complex path
    graph.add_edge("react_agent", "rag_confidence")
    graph.add_edge("rag_confidence", "model_router")
    # model_router → direct_responder (reuses same node for final call)

    graph.add_edge("response_validator", "output_normalizer")
    graph.add_edge("output_normalizer", "observability")
    graph.add_edge("observability", "memory_update")
    graph.add_edge("memory_update", END)

    return graph.compile()


mhc_graph = build_graph()
