from langchain_openai import ChatOpenAI
from openai import OpenAI
from used_models.llm.BaseLLM import BaseLLM
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
from pipeline_config import settings, OPENAI_API_KEY

LLM_MODEL = settings.config["llm_model"]
default_reasoning_effort = "minimal"

class OpenAIWrapper(BaseLLM):
    def __init__(self, model=LLM_MODEL):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = model
        
        kwargs = {"model": model, "api_key": OPENAI_API_KEY}
        if model.startswith("gpt-5"):
            kwargs["reasoning"] = {"effort": default_reasoning_effort}
        else:
            kwargs["temperature"] = 0
            
        self.lcModel = ChatOpenAI(**kwargs)
        # self.lcModel = ChatOpenAI(model=model, temperature=0, api_key=OPENAI_API_KEY)
    
    def invoke(self, messages):
        response = self.lcModel.invoke(messages)

        # ChatOpenAI may expose Responses API output as content blocks (for
        # example, a reasoning block followed by the final text block). The
        # graph expects response.content to remain a plain string.
        if isinstance(response.content, str):
            return response

        if isinstance(response.content, list):
            for block in reversed(response.content):
                if (
                    isinstance(block, dict)
                    and isinstance(block.get("text"), str)
                    and block["text"].strip()
                ):
                    response.content = block["text"]
                    return response

        # Preserve the graph's existing empty-answer / fallback path when a
        # provider response contains no usable final-text block.
        response.content = "[]"
        return response
    
    
    def generate(self, system_prompt, content, reasoning_effort=default_reasoning_effort):
        kwargs = {
            "model": self.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        }

        if self.model.startswith("gpt-5"):
            kwargs["reasoning"] = {"effort": reasoning_effort}
        else:
            kwargs["temperature"] = 0

        response = self.client.responses.create(**kwargs)

        return response.output_text
  

    def generate_structured(
        self,
        system_prompt: str,
        content: str,
        response_model: type[T],
        reasoning_effort: str = default_reasoning_effort,
    ) -> T:
        kwargs = {
            "model": self.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "text_format": response_model,
        }

        if self.model.startswith("gpt-5"):
            kwargs["reasoning"] = {"effort": reasoning_effort}
        else:
            kwargs["temperature"] = 0

        response = self.client.responses.parse(**kwargs)

        if response.output_parsed is None:
            raise ValueError(
                f"Model did not return a valid {response_model.__name__}"
            )

        return response.output_parsed

