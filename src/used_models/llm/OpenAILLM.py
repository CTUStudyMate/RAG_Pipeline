from langchain_openai import ChatOpenAI
from openai import OpenAI
from used_models.llm.BaseLLM import BaseLLM
from pipeline_config import settings, OPENAI_API_KEY
LLM_MODEL = settings.config["llm_model"]
default_reasoning_effort = "low"
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
        return self.lcModel.invoke(messages)   
    
    
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
  

    
    
    
    
