from PIPELINE._5_generate.OllamaLLM import OllamaWrapper
from PIPELINE._5_generate.OpenAILLM import OpenAIWrapper


def get_llm(provider="openai"):
    if provider == "openai":
        return OpenAIWrapper()
    elif provider == "ollama":
        return OllamaWrapper()
    else:
        raise ValueError("Unsupported provider")