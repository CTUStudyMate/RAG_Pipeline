from src.app.chat_flow.chatflow_graph import chatflow_graph
from pipeline_setup import cursor
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
            "cursor": cursor
        })
        messages = chat_data["messages"]
        print(f"- {messages[-1].content}")