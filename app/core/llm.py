from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings


def get_llm(temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    """Devuelve la instancia centralizada del modelo Gemini."""
    return ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        temperature=temperature,
        google_api_key=settings.GOOGLE_API_KEY,
    )
