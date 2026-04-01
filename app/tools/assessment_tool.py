from app.rag.retriever import retrieve


class AssessmentTool:
    async def run(self, query: str) -> dict:
        return await retrieve("assessment", query)
