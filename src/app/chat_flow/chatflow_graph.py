from typing import Annotated, Any, Optional, Sequence, TypedDict, List
from PIPELINE._6_citation_postprocessing.validate_citation import merge_segments_to_text
from app.chat_flow.rewrite_query_graph import rewrite_query_graph
from app.chat_flow.utils import llm_conversational_fallback
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, add_messages, START, END
from app.chat_flow.intent_route_graph import intent_graph
from app.chat_flow.generate_rag_graph import generate_graph
from app.chat_flow.retrieve_graph import retrieve_graph
from app.chat_flow.validate_graph import validate_graph
from app.chat_flow.generate_vanilla_graph import generate_vanilla_graph

debug = True

# user asks => need rag? => no: direct answer
#                            | 
#                           yes: rewrite query => retrieve => generate => citation validate

class SegmentState(TypedDict):
    raw: List[dict]
    validated: Optional[List[dict]]
    
class ChatFlowState(TypedDict):
    """State for chatbot with message history."""
    intent: str
    messages: Annotated[Sequence[BaseMessage], add_messages] # ALL
    
    docs: list
    query: str 
    rewritten_query: str | None
    
    # for ui
    user_message: HumanMessage
    last_ai_message_segments: SegmentState | None
    
    # external param
    cursor: Any


def identify_user_intent_node(state: ChatFlowState):
    result = intent_graph.invoke({
        "query": state["query"]
    })
    if debug: print(f"1 - user intent: {result["intent"]}")
    return {
        "intent": result["intent"]
    }

def route_regarding_intent(state: ChatFlowState):
    intent = state["intent"]
    if debug: print(f"    need retrieve?: {intent == "need_retrieve"}")
    if intent == "need_retrieve":
        return "need_retrieve"
    else:
        return "no_retrieve"

# no rag    
def generate_vanilla_node(state: ChatFlowState):
    result = generate_vanilla_graph.invoke({
        "messages": state["messages"],
        "query": state["query"]
    })
    if debug: print("2 - Vanilla generate: ", result["parsed"])
    return {
        "messages": [result["user_message"]],
        "last_ai_message_segments": {
            "raw": result["parsed"],
            "validated": result["parsed"],
        }
    }
    

# rag
def rewrite_query_node(state: ChatFlowState):
    result = rewrite_query_graph.invoke({
        "messages": state["messages"],
        "query": state["query"]
    })
    if debug: print("2 - Rewrite query: ", result["rewritten_query"])
    return {
        "rewritten_query": result["rewritten_query"] # already fallback to user query if it is not rewritten
    }
    
def retrieve_node(state: ChatFlowState):
    result = retrieve_graph.invoke({
        "rewritten_query": state["rewritten_query"],
        "cursor": state["cursor"],
    })
    if debug: 
        print(f"3 - Retrieved {len(result["docs"]):}")
        for doc in result["docs"]:
            print(f"    {doc["text"][:100]}")
        
    return {
        "docs": result["docs"]
    }
        
def generate_rag_node(state: ChatFlowState):
    result = generate_graph.invoke({
        "docs": state["docs"],
        "query": state["query"],
        "cursor": state["cursor"]
    })
    if debug: print("4 - RAG generate: ", result["parsed"])

    return {
        "messages": [result["user_message"]],
        "last_ai_message_segments": {
            "raw": result["parsed"],
            "validated": None,
        }
    }       
        
        
def validate_citation_node(state: ChatFlowState):
    segments_obj = state.get("last_ai_message_segments")

    if not segments_obj or not segments_obj.get("raw"):
        return {
            "last_ai_message_segments": {
                "raw": None,
                "validated": None
            }
        }

    result = validate_graph.invoke({
        "segments": segments_obj["raw"],
        "docs": state["docs"]
    })

    if debug: print("5 - Citation validate: ", result["segments"])
    return {
        "last_ai_message_segments": {
            **segments_obj,
            "validated": result["segments"]
        }
    }
    
def final_answer_and_messages_handle_node(state: ChatFlowState):
    segments_obj = state.get("last_ai_message_segments")

    ABSTAIN = [{
        "type": "abstained",
        "segment": "The system can't answer this question. Please try again with another question.",
        "citation": [],
        "role": "paragraph"
    }]

    if not segments_obj:
        valid_segments = ABSTAIN
        raw_segments = None
    else:
        valid_segments = segments_obj.get("validated")
        raw_segments = segments_obj.get("raw")
        
        # in case utterance ở bước intent bị sót case
        if not valid_segments or (len(valid_segments)==1 and valid_segments[0]["type"]=="abstained"):
            try:
                print("The system has already attempted to retrieve relevant documents but could not find enough information to answer the user's question. Fallback to conversational llm check.")
                valid_segments = llm_conversational_fallback(state=state)["parsed"]
            except Exception as e:
                print(e)
                valid_segments = ABSTAIN    

    formatted_answer = merge_segments_to_text(valid_segments)

    ai_msg = AIMessage(
        content=formatted_answer,
        additional_kwargs={
            "segments": valid_segments,
            # "debug": {
            #     "has_segments": segments_obj if segments_obj is not None else None
            # }
        }
    )
    if debug: print("6 - Final: ", ai_msg)
    return {
        "last_ai_message_segments": {
            "raw": raw_segments,
            "validated": valid_segments
        },
        "messages": [ai_msg]
    }
    
# WIRING FULL GRAPH
## Node names
identify_intent = "identify_intent"
generate_vanilla = "generate_vanilla"
rewrite_query = "rewrite_query"
retrieve = "retrieve"
generate_rag = "generate_rag"
validate_citation = "validate_citation"
final = "final_answer_and_messages_handle"

## Graph nodes
graph = StateGraph(ChatFlowState)

graph.set_entry_point(identify_intent)
graph.add_node(identify_intent, identify_user_intent_node)

# no rag branch
graph.add_node(generate_vanilla, generate_vanilla_node)

# rag branch
graph.add_node(rewrite_query, rewrite_query_node)
graph.add_node(retrieve, retrieve_node)
graph.add_node(generate_rag, generate_rag_node)
graph.add_node(validate_citation, validate_citation_node)

# final
graph.add_node(final, final_answer_and_messages_handle_node)
graph.set_finish_point(final)


graph.add_conditional_edges(identify_intent, route_regarding_intent, {
    "need_retrieve": rewrite_query,
    "no_retrieve": generate_vanilla
})
graph.add_edge(rewrite_query, retrieve)
graph.add_edge(retrieve, generate_rag)
graph.add_edge(generate_rag, validate_citation)
graph.add_edge(validate_citation, final)

graph.add_edge(generate_vanilla, final)

chatflow_graph = graph.compile()
    
# TEST ********************************************
# import psycopg
# from pipeline_config import settings
# pgdb_connect_info = settings.pgdb_connect_info

# conn = psycopg.connect(
# host=pgdb_connect_info.host,
# port=pgdb_connect_info.port,
# dbname=pgdb_connect_info.db_name,
# user=pgdb_connect_info.user,
# password=pgdb_connect_info.password
# )
# cursor = conn.cursor()

# result = chatflow_graph.invoke({
#     "query": "What is software engineering and how does it fit into computer science?",
#     "cursor": cursor
# })

      