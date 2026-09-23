from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from domain.config import get_settings


@lru_cache
def get_supervisor_model() -> BaseChatModel:
    settings = get_settings()
    return init_chat_model(settings.supervisor_model, temperature=0)


@lru_cache
def get_retrieval_answer_model() -> BaseChatModel:
    settings = get_settings()
    return init_chat_model(settings.retrieval_answer_model, temperature=0.2)


@lru_cache
def get_council_chair_model() -> BaseChatModel:
    settings = get_settings()
    return init_chat_model(settings.council_chair_model, temperature=0.2)
