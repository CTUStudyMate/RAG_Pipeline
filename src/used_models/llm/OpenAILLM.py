from langchain_openai import ChatOpenAI
from openai import OpenAI
from used_models.llm.BaseLLM import BaseLLM
from pipeline_config import settings, OPENAI_API_KEY

LLM_MODEL = settings.config["llm_model"]
class OpenAIWrapper(BaseLLM):
    def __init__(self, model=LLM_MODEL):
        self.client = OpenAI()
        self.model = model
        self.lcModel = ChatOpenAI(model=model, temperature=0, api_key=OPENAI_API_KEY)
    
    def invoke(self, messages):
        return self.lcModel.invoke(messages)   
    
    
    def generate(self, system_prompt, content):
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content":system_prompt},
                {"role": "user",
                "content":content}
            ],
            temperature=0, #seed
        )

        return response.output_text
    
    
    
    