class MemoryReadTool:
    async def run(self, user_id: str) -> dict:
        try:
            from app.services.session_service import SessionService
            svc = SessionService()
            history = await svc.get_recent_history(user_id, session_id=None, n=5)
            summary = await svc.get_latest_summary(user_id)
            return {"history": history, "summary": summary}
        except Exception as e:
            return {"history": [], "summary": None, "error": str(e)}
