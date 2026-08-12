from app.services.qa_and_excercises.curated_qa import CuratedQaBatch, VerifiableQaGenerateRequest, generate_curated_qas
from app.services.qa_and_excercises.excercise import CuratedQaToRagEngine, GenerateExercisesResponse, generate_exercises
from app.services.chat_title import (
    ChatTitleGenerationError,
    ChatTitleServiceUnavailableError,
    generate_chat_title,
)
from app.services.rag_data.chunks import ChunkNotFoundException, DatabaseConnectionException, DatabaseException, ImageNotFoundException, get_chunk_texts_from_db, get_image_from_db
from app.routes.documents import router as document_router
from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel, ValidationError, field_validator
from src.app.chat_flow.chatflow_graph import ChatFlowState, chatflow_graph 
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from fastapi.responses import Response
from typing import Any, List
from fastapi import Query
import base64


app = FastAPI() 
app.include_router(document_router)


class GenerateChatTitleRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must be a non-empty user message")
        return value


def normalize_chat_segments(segments: object) -> list[dict[str, Any]]:
    """Return segments that satisfy the response contract expected by MainBackend."""
    normalized: list[dict[str, Any]] = []

    if isinstance(segments, list):
        for item in segments:
            if not isinstance(item, dict):
                continue

            text = item.get("segment")
            if not isinstance(text, str) or not text.strip():
                continue

            role = item.get("role")
            segment_type = item.get("type")
            citations = item.get("citations")

            normalized.append({
                **item,
                "role": role if isinstance(role, str) and role else "paragraph",
                "type": segment_type if isinstance(segment_type, str) and segment_type else "inferred",
                "segment": text,
                "citations": citations if isinstance(citations, list) else [],
            })

    return normalized or [{
        "role": "paragraph",
        "type": "abstained",
        "segment": "The system can't answer this question. Please try again with another question.",
        "citations": [],
    }]


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

    segments = normalize_chat_segments(
        last_ai_message.additional_kwargs.get("segments", [])
    )

    return {
        "content": last_ai_message.content,
        "segments": segments,
        "need_verify": result["intent"] == "need_retrieve",
        "rewritten_question": result.get("rewritten_query"),
        "document_ids": document_ids
    }
    
    
@app.post("/generate-chat-title", response_model=str)
async def get_chat_title(payload: Any = Body(...)) -> str:
    try:
        request = GenerateChatTitleRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "chat_title:invalid_content",
                "cause": "content must be a non-empty user message.",
            },
        ) from exc

    try:
        return await generate_chat_title(request.content)
    except ChatTitleServiceUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "chat_title:service_unavailable",
                "cause": str(exc),
            },
        ) from exc
    except ChatTitleGenerationError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "chat_title:generation_failed",
                "cause": str(exc),
            },
        ) from exc
    
@app.post("/generate-curated-qas")
async def get_generated_curated_qas(payload: VerifiableQaGenerateRequest):
    curated_qas: CuratedQaBatch = await generate_curated_qas(payload)
    return curated_qas

@app.post("/generate-exercises")
async def get_generated_excercises(payload:  CuratedQaToRagEngine):
    exercises: GenerateExercisesResponse = await generate_exercises(payload)
    return exercises
