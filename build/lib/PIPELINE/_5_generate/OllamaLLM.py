import ollama

from PIPELINE._5_generate.BaseLLM import BaseLLM
from pipeline_config import LLM_MODEL

class OllamaWrapper(BaseLLM):
    def __init__(self, model=LLM_MODEL):
        self.model = model

    def generate(self, prompt, images=None):
        msg = {
            "role": "user",
            "content": prompt
        }

        if images:
            clean_images = []
            for img in images:
                if img.startswith("data:image"):
                    img = img.split(",")[1]
                clean_images.append(img)

            msg["images"] = clean_images

        response = ollama.chat(
            model=self.model,
            messages=[msg]
        )

        return response["message"]["content"]