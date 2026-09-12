from pipeline_setup import llm
answer = llm.generate(system_prompt="Be a nice teacher.", content="Hello")
print(answer)
