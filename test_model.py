import time

from openai import OpenAI
from dotenv import load_dotenv

import os

from used_models.llm.OpenAILLM import OpenAIWrapper

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

generate_start = time.perf_counter()
response = client.responses.create(
    model="gpt-5-nano",
    input="what is software engineering?",
        reasoning={
        "effort": "minimal"
    }
)
# self = OpenAIWrapper()    
# print(self.lcModel.invoke("what is software engineering?").response_metadata)  
generate_end = time.perf_counter()

print(response.output_text)
print(generate_end-generate_start)