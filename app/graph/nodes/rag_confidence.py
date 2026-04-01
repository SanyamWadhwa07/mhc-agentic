async def rag_confidence_node(state):
    tool_results = state.get("tool_results", [])

    all_scores = []
    for tr in tool_results:
        result = tr.get("result", {})
        if isinstance(result, dict) and "scores" in result:
            all_scores.extend(result["scores"])

    if not all_scores:
        rag_confidence = 1.0  # no RAG used → not a confidence problem
    else:
        rag_confidence = sum(all_scores) / len(all_scores)

    return {**state, "rag_confidence": round(rag_confidence, 3)}
