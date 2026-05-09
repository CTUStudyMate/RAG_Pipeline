
from src.used_models.llm.OllamaLLM import OllamaWrapper
from src.used_models.llm.OpenAILLM import OpenAIWrapper

def get_llm(provider="openai"):
    if provider == "openai":
        return OpenAIWrapper()
    elif provider == "ollama":
        return OllamaWrapper()
    else:
        raise ValueError("Unsupported provider")