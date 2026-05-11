from openai import OpenAI
from used_models.llm.BaseLLM import BaseLLM
from used_models.schema.llm_answer_schema import AnswerSchema
from pipeline_config import LLM_MODEL


class OpenAIWrapper(BaseLLM):
    def __init__(self, model=LLM_MODEL):
        self.client = OpenAI()
        self.model = model

    # def generate(self, system_prompt, prompt, images=None):
    #     content = [{"type": "input_text", "text": prompt}]

    #     if images:
    #         for img in images:
    #             content.append({
    #                 "type": "input_image",
    #                 "image_url": img["data"]
    #             })

    #     response = self.client.responses.create(
    #         model=self.model,
    #         input=[
    #             {"role": "system", "content":system_prompt},
    #             {"role": "user",
    #             "content":content}
    #         ],
    #         temperature=0,
    #         top_p=1
    #     )

    #     return response.output_text
    
    def generate(self, system_prompt, content):
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content":system_prompt},
                {"role": "user",
                "content":content}
            ],
            temperature=0,
            top_p=1
        )

        return response.output_text
    
    