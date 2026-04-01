from app.rag.retriever import retrieve


class ResourceTool:
    async def run(self, query: str) -> dict:
        return await retrieve("resource", query)
