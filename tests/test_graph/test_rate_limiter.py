import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_rate_limiter_fails_open_on_redis_error():
    from app.graph.nodes.rate_limiter import rate_limiter_node
    state = {"user_id": "test_user", "message": "hello"}

    with patch("redis.asyncio.from_url", side_effect=Exception("Redis down")):
        result = await rate_limiter_node(state)

    assert result.get("is_rate_limited") == False


@pytest.mark.asyncio
async def test_rate_limiter_blocks_when_exceeded():
    from app.graph.nodes.rate_limiter import rate_limiter_node
    state = {"user_id": "test_user", "message": "hello"}

    mock_pipe = AsyncMock()
    mock_pipe.execute = AsyncMock(return_value=[None, None, 99, None])  # 99 requests

    mock_redis = AsyncMock()
    mock_redis.pipeline = AsyncMock(return_value=mock_pipe)
    mock_redis.aclose = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        result = await rate_limiter_node(state)

    assert result.get("is_rate_limited") == True
