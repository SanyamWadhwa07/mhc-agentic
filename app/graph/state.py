from typing import TypedDict, Optional, List, Dict, Any


class MHCState(TypedDict):
    # Input
    user_id: str
    session_id: str
    message: str

    # Safety
    is_crisis: bool
    crisis_response: Optional[str]
    is_rate_limited: bool
    sanitized_message: str

    # Emotional
    emotional_intensity: float

    # Path
    path: str  # "simple" | "complex" | "crisis"
    complexity_score: float

    # ReAct
    react_steps: int
    tool_results: List[Dict[str, Any]]
    rag_confidence: float

    # Model selection
    model_used: str

    # Memory
    session_history: List[Dict[str, Any]]
    session_summary: Optional[str]
    last_risk_level: str

    # Output
    response: str
    emotions: List[str]
    risk_level: str
    clinical_flags: List[str]
    referral_needed: bool

    # Observability
    metrics: Dict[str, Any]
    start_time: float
