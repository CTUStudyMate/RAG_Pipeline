from fastapi import FastAPI 
from src.app.chat_flow.chatflow_graph import chatflow_graph 
app = FastAPI() 
@app.get("/") 
def root(): 
    return {"status": "ok"} 

@app.post("/chat") 
def chat(payload: dict): 
    result = chatflow_graph.invoke({ 
        "messages": payload.get("messages", []), 
        "query": payload["query"]
    }) 
    return {
        "content": result["messages"][-1].content,
        "segments": result["messages"][-1].additional_kwargs["segments"]
    }