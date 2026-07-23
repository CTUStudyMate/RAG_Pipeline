from app.services.qa_and_excercises.curated_qa import CuratedQaBatch, VerifiableQaGenerateRequest, generate_curated_qas
from app.services.rag_data.chunks import ChunkNotFoundException, DatabaseConnectionException, DatabaseException, ImageNotFoundException, get_chunk_texts_from_db, get_image_from_db
from fastapi import FastAPI, HTTPException 
from src.app.chat_flow.chatflow_graph import ChatFlowState, chatflow_graph 
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from fastapi.responses import Response
from typing import List
from fastapi import Query
import base64

app = FastAPI() 
@app.get("/") 
def root(): 
    return {"status": "ok"} 


@app.get("/chunks/text")
def get_chunk_texts(chunk_ids: List[str] = Query(...)):
    try:
        chunks = get_chunk_texts_from_db(chunk_ids=chunk_ids)
        return chunks

    except ChunkNotFoundException as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except DatabaseConnectionException as e:
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )

    except DatabaseException as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/chunks/images/{image_id}")
def get_image(image_id: str):
    try:
        img = get_image_from_db(img_id=image_id)
        data = img[2].split(",")[1]
        image_bytes = base64.b64decode(data)

        return Response(
            content=image_bytes,
            media_type="image/png"
        )

    except ImageNotFoundException as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except DatabaseConnectionException as e:
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )

    except DatabaseException as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to decode image: {e}"
        )
            

@app.post("/chat")
def chat(payload: dict):
    payload_messages = payload.get("messages", [])

    messages = [
        HumanMessage(content=m.get("content", ""))
        if m.get("sender_type") == "user"
        else AIMessage(content=m.get("content", ""))
        for m in payload_messages
    ]

    result: ChatFlowState = chatflow_graph.invoke(
        {
            "messages": messages,
            "query": payload["query"],
        }
    )

    last_ai_message = result["messages"][-1]
    
    # get document ids
    document_ids = []
    for doc in result.get("docs", []):
        metadata = doc.get("metadata")
        if not metadata:
            continue
        document_id = metadata.get("document")
        if not document_id:
            continue
        if document_id not in document_ids:
            document_ids.append(document_id)

    return {
        "content": last_ai_message.content,
        "segments": last_ai_message.additional_kwargs.get("segments", []),
        "need_verify": result["intent"] == "need_retrieve",
        "rewritten_question": result.get("rewritten_query"),
        "document_ids": document_ids
    }
    
    
@app.post("/chat-title")    
def get_chat_title(message: str):
    return {
        "title": "Temp title from RAG",
    }
    
@app.post("/generate-curated-qas")
async def get_generated_curated_qas(payload: VerifiableQaGenerateRequest):
    curated_qas: CuratedQaBatch = await generate_curated_qas(payload)
    return curated_qas