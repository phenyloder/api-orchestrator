import os
import threading
import logging
from langchain_openai import AzureChatOpenAI
from .token_manager import get_token
from ..config import settings

logger = logging.getLogger("llm_model")

class LLMModel:
    _lock = threading.Lock()
    _llm = None
    _last_token = None

    @classmethod
    def get_llm(cls):
        token = get_token()
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", None)
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", None)
        api_type = os.getenv("AZURE_OPENAI_API_TYPE", None)
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", None)
        user_appkey = os.getenv("AZURE_OPENAI_USER_APPKEY", None)

        with cls._lock:
            if cls._llm is None or cls._last_token != token:
                try:
                    logger.info("Creating new AzureChatOpenAI LLM instance...")
                    kwargs = dict(
                        azure_endpoint=azure_endpoint,
                        openai_api_version=api_version,
                        openai_api_type=api_type,
                        openai_api_key=token,
                        deployment_name=deployment_name,
                        temperature=settings.temperature,
                        user=user_appkey,
                    )
                    cls._llm = AzureChatOpenAI(**kwargs)
                    cls._last_token = token
                    logger.info("New LLM instance created.")
                except Exception as e:
                    logger.error(f"Failed to create LLM: {e}")
                    raise
            return cls._llm 