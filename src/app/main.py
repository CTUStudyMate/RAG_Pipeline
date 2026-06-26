from fastapi import FastAPI 
from src.app.chat_flow.chatflow_graph import chatflow_graph 
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

app = FastAPI() 
@app.get("/") 
def root(): 
    return {"status": "ok"} 

@app.post("/chat") 
def chat(payload: dict): 
    payload_messages = payload.get("messages", [])
    messages = [HumanMessage(content=m.get("content", "")) if m.get("sender_type") == "user" else AIMessage(content=m.get("content", "")) for m in payload_messages]
    result = chatflow_graph.invoke({ 
        "messages": messages, 
        "query": payload["query"]
    }) 
    return {
        "content": result["messages"][-1].content,
        "segments": result["messages"][-1].additional_kwargs["segments"]
    }