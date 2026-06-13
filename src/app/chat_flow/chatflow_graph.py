from typing import Annotated, Any, Optional, Sequence, TypedDict, List
from PIPELINE._6_citation_postprocessing.validate_citation import merge_segments_to_text
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, add_messages, START, END
from app.chat_flow.intent_route_graph import intent_graph
from app.chat_flow.generate_rag_graph import generate_graph
from app.chat_flow.retrieve_graph import retrieve_graph
from app.chat_flow.validate_graph import validate_graph
from app.chat_flow.generate_vanilla_graph import generate_vanilla_graph


# user asks => rewrite query => direct answer
#                            | 
#                            => retrieve => generate => cite

class SegmentState(TypedDict):
    raw: List[dict]
    validated: Optional[List[dict]]
    
class ChatFlowState(TypedDict):
    """State for chatbot with message history."""
    intent: str
    messages: Annotated[Sequence[BaseMessage], add_messages]
    last_ai_message_segments: SegmentState | None

    docs: list
    query: str # chưa rewrite thì là user query, rewrite rồi thì là rewritten query
    cursor: Any

def identify_user_intent_node(state: ChatFlowState):
    result = intent_graph.invoke({
        "query": state["query"]
    })
    return {
        "intent": result["intent"]
    }

def route_regarding_intent(state: ChatFlowState):
    intent = state["intent"]
    if intent == "need_retrieve":
        return "need_retrieve"
    else:
        return "no_retrieve"
    
def generate_vanilla_node(state: ChatFlowState):
    result = generate_vanilla_graph.invoke({
        "messages": state["messages"],
        "query": state["query"]
    })
    return {
        "messages": [result["user_message"]],
        "last_ai_message_segments": {
            "raw": result["parsed"],
            "validated": None,
        }
    }
    

def retrieve_node(state: ChatFlowState):
    result = retrieve_graph.invoke({
        "query": state["query"],
        "cursor": state["cursor"],
    })
    return {
        "docs": result["docs"]
    }
        
def generate_node(state: ChatFlowState):
    result = generate_graph.invoke({
        "docs": state["docs"],
        "query": state["query"],
        "cursor": state["cursor"]
    })

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
        valid_segments = segments_obj.get("validated") or ABSTAIN
        raw_segments = segments_obj.get("raw")

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
intent_route = "intent_route"
generate_vanilla = "generate_vanilla"
retrieve = "retrieve"
generate = "generate"
validate_citation = "validate_citation"
final = "final_answer_and_messages_handle"

## Graph nodes
graph = StateGraph(ChatFlowState)

graph.set_entry_point(identify_intent)

graph.add_node(identify_intent, identify_user_intent_node)
graph.add_node(intent_route, route_regarding_intent)

graph.add_node(generate_vanilla, generate_vanilla_node)

graph.add_node(retrieve, retrieve_node)
graph.add_node(generate, generate_node)
graph.add_node(validate_citation, validate_citation_node)

graph.add_node(final, final_answer_and_messages_handle_node)

graph.set_finish_point(final)

graph.add_edge(identify_intent, intent_route)
graph.add_conditional_edges(intent_route, route_regarding_intent, {
    "need_retrieve": retrieve,
    "no_retrieve": generate_vanilla
})
graph.add_edge(retrieve, generate)
graph.add_edge(generate, validate_citation)
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
    
# print(result["messages"][-1])    
      