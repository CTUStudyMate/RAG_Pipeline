from openai import OpenAI

from PIPELINE._5_generate.BaseLLM import BaseLLM
from pipeline_config import LLM_MODEL


class OpenAIWrapper(BaseLLM):
    def __init__(self, model=LLM_MODEL):
        self.client = OpenAI()
        self.model = model

    def generate(self, prompt, images=None):
        content = [{"type": "text", "text": prompt}]

        if images:
            for img in images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img}
                })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            temperature=0
        )

        return response.choices[0].message.content