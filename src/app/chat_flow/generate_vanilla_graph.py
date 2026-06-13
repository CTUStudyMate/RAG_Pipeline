from typing import Annotated, Sequence, TypedDict, List, Optional
from PIPELINE._4_retrieve.multi_stages.multi_stages_retriever import multi_stages_retrieve
from PIPELINE._5_generate.generate import JSON_FIX_PROMPT, build_content_inputs_lcver, absenceBasedAbstain_system_prompt, evidenceBasedSynthesis_system_prompt
from app.chat_flow.generate_rag_graph import trim_messages
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, add_messages
from typing_extensions import TypedDict
from typing import Any
import json

from pipeline_setup import llm

class GenerateVanillaState(TypedDict):
    """State for generating answer with message history without retrieved docs."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_message: HumanMessage
    parsed: Optional[List[dict]] # this is the code-processed input, not json parsed from llm's answer
    query: str

def recieve_user_message_node(state: GenerateVanillaState):
    user_query = state["query"]
    user_message = HumanMessage(content=user_query)
    return {
        "messages": user_message, # append to the list for calling llm with history
        "user_message": user_message # for final expose state in flow graph
    }
 
system_prompt = """
You are an academic study assistant for Can Tho University.
Be supportive, encouraging, and engaging in conversations, help students stay motivated in their studies.
"""
    
def generate_vanilla(state: GenerateVanillaState):
    last_messages = trim_messages(state["messages"])
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            *last_messages
        ])
        raw_ans = response.content
        raw_ans_segments = [
            {
                "type": "conversational",
                "segment": raw_ans,
                "citation": [],
                "role": "paragraph"
            }
        ]
        return {
            "parsed": raw_ans_segments
        }
    except Exception as e:
        print(e)
        return {
            "parsed": [{
                "type": "abstained",
                "segment": "The system can't answer this question. Please try again with another question.",
                "citation": [],
                "role": "paragraph"
            }]
        }     
 
graph = StateGraph(GenerateVanillaState)

graph.add_node("generate_vanilla", generate_vanilla)

graph.set_entry_point("generate_vanilla")
graph.set_finish_point("generate_vanilla")


generate_vanilla_graph = graph.compile()    