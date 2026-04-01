import pytest


@pytest.mark.asyncio
async def test_high_emotional_intensity():
    from app.graph.nodes.emotional_scorer import emotional_scorer_node
    state = {"sanitized_message": "BAHUT ZYADA dard ho raha hai!!! rona aa raha hai baar baar!!!"}
    result = await emotional_scorer_node(state)
    assert result["emotional_intensity"] > 0.5


@pytest.mark.asyncio
async def test_low_emotional_intensity():
    from app.graph.nodes.emotional_scorer import emotional_scorer_node
    state = {"sanitized_message": "aaj mausam kaisa hai"}
    result = await emotional_scorer_node(state)
    assert result["emotional_intensity"] < 0.4
