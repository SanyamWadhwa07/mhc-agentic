import pytest


@pytest.mark.asyncio
async def test_clinical_keywords_route_complex():
    from app.graph.nodes.path_classifier import path_classifier_node
    state = {
        "sanitized_message": "mujhe bahut depression feel hoti hai",
        "session_history": [],
        "last_risk_level": "low",
        "emotional_intensity": 0.3,
    }
    result = await path_classifier_node(state)
    assert result["path"] == "complex"


@pytest.mark.asyncio
async def test_simple_greeting_routes_simple():
    from app.graph.nodes.path_classifier import path_classifier_node
    state = {
        "sanitized_message": "hi",
        "session_history": [],
        "last_risk_level": "low",
        "emotional_intensity": 0.1,
    }
    result = await path_classifier_node(state)
    assert result["path"] == "simple"


@pytest.mark.asyncio
async def test_prior_high_risk_always_complex():
    from app.graph.nodes.path_classifier import path_classifier_node
    state = {
        "sanitized_message": "aaj theek hoon",
        "session_history": [],
        "last_risk_level": "high",
        "emotional_intensity": 0.2,
    }
    result = await path_classifier_node(state)
    assert result["path"] == "complex"
