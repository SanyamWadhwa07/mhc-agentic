import json
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from groq import AsyncGroq
from app.config import settings

log = structlog.get_logger()


class LLMService:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.fallback_triggered = False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=False
    )
    async def _call_model(self, model: str, messages: list, response_format: dict = None) -> str:
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def call(self, model: str, messages: list, response_format: dict = None) -> tuple[str, str]:
        """Returns (content, actual_model_used)"""
        try:
            content = await self._call_model(model, messages, response_format)
            return content, model
        except Exception as e:
            log.error("primary_model_failed", model=model, error=str(e))

            # Fallback hierarchy: quality model → fast model → template
            if model == settings.quality_response_model:
                try:
                    log.warning("fallback_to_70b")
                    self.fallback_triggered = True
                    content = await self._call_model(settings.groq_quality_model, messages, response_format)
                    return content, settings.groq_quality_model
                except Exception as e2:
                    log.error("fallback_70b_failed", error=str(e2))

            if model in [settings.quality_response_model, settings.groq_quality_model]:
                try:
                    log.warning("fallback_to_fast_model")
                    self.fallback_triggered = True
                    content = await self._call_model(settings.groq_fast_model, messages, response_format)
                    return content, settings.groq_fast_model
                except Exception as e3:
                    log.error("fallback_fast_failed", error=str(e3))

            # Last resort template
            log.error("all_models_failed", using="template")
            self.fallback_triggered = True
            template = {
                "response": "Main abhi tumhare saath hoon. Thodi si technical problem aa gayi hai, but main sun raha/rahi hoon. Agar tumhe turant madad chahiye, please iCall (9152987821) ya Vandrevala (1860-2662-345) pe call karo. 💙",
                "emotions": ["distress"],
                "risk_level": "medium",
                "clinical_flags": [],
                "referral_needed": True
            }
            return json.dumps(template), "template"
