from fastapi import FastAPI 
from src.app.chat_flow.chatflow_graph import chatflow_graph 
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

app = FastAPI() 
@app.get("/") 
def root(): 
    return {"status": "ok"} 

@app.get("/chunks/{chunk_id}/text")
def get_chunk_text(chunk_id):
    

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
    
@app.post("/chat-title")    
def get_chat_title(message: str):
    return {
        "title": "Temp title from RAG",
    }