from app.rag.retriever import retrieve


class TherapyTool:
    async def run(self, query: str) -> dict:
        return await retrieve("therapy", query)
