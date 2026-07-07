from src.app.chat_flow.chatflow_graph import chatflow_graph
from pipeline_setup import pool
messages = []
print("chat bot started.")



while True:
    question = input("Enter message: ")
    if question.lower() == "quit":
        break
    else:
        chat_data = chatflow_graph.invoke({
            "messages": messages,
            "query": question,
            "connection_pool": pool
        })
        messages = chat_data["messages"]
        print(f"- {messages[-1].content}")