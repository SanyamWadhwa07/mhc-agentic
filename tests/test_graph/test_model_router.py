import pytest


@pytest.mark.asyncio
async def test_high_risk_routes_to_120b():
    from app.graph.nodes.model_router import model_router_node
    from app.config import settings
    state = {"risk_level": "high", "emotional_intensity": 0.3, "rag_confidence": 0.8, "react_steps": 1}
    result = await model_router_node(state)
    assert result["model_used"] == settings.quality_response_model


@pytest.mark.asyncio
async def test_low_risk_routes_to_70b():
    from app.graph.nodes.model_router import model_router_node
    from app.config import settings
    state = {"risk_level": "low", "emotional_intensity": 0.3, "rag_confidence": 0.8, "react_steps": 1}
    result = await model_router_node(state)
    assert result["model_used"] == settings.groq_quality_model


@pytest.mark.asyncio
async def test_low_rag_confidence_routes_to_120b():
    from app.graph.nodes.model_router import model_router_node
    from app.config import settings
    state = {"risk_level": "low", "emotional_intensity": 0.3, "rag_confidence": 0.3, "react_steps": 1}
    result = await model_router_node(state)
    assert result["model_used"] == settings.quality_response_model
