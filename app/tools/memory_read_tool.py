class MemoryReadTool:
    async def run(self, user_id: str, session_id: str = None) -> dict:
        try:
            from app.services.session_service import SessionService
            svc = SessionService()
            history = await svc.get_recent_history(user_id, session_id=session_id, n=5)
            summary = await svc.get_latest_summary(user_id, session_id=session_id)
            return {"history": history, "summary": summary}
        except Exception as e:
            return {"history": [], "summary": None, "error": str(e)}
