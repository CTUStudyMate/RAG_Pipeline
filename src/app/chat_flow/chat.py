from src.app.chat_flow.chatflow_graph import chatflow_graph

messages = []
print("chat bot started.")

import psycopg
from pipeline_config import settings
pgdb_connect_info = settings.pgdb_connect_info

conn = psycopg.connect(
host=pgdb_connect_info.host,
port=pgdb_connect_info.port,
dbname=pgdb_connect_info.db_name,
user=pgdb_connect_info.user,
password=pgdb_connect_info.password
)
cursor = conn.cursor()

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