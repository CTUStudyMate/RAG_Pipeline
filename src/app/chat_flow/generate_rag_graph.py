from typing import Annotated, Sequence, TypedDict, List, Optional
from PIPELINE._4_retrieve.multi_stages.multi_stages_retriever import multi_stages_retrieve
from PIPELINE._5_generate.generate import JSON_FIX_PROMPT, build_content_inputs_lcver, absenceBasedAbstain_system_prompt, evidenceBasedSynthesis_system_prompt
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, add_messages
from typing_extensions import TypedDict
from typing import Any
import json

from pipeline_setup import llm

class GenerateState(TypedDict):
    """State for generating answer with message history and retrieved docs."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_message: HumanMessage # for final state expose to the flow graph so that the flow only appends this message, not the whole list above
    # raw outputs
    raw_output: str
    parsed: Optional[List[dict]]

    # control flags
    pass_stage: str   # "pass1" | "pass2" | "done"
    retry_count: int

    # external data
    docs: list
    query: str
    cursor: Any


# HELPERS
def trim_messages(messages: list[BaseMessage], k: int = 10):
    """
    Keep last k messages (excluding system messages)
    """
    return messages[-k:]
    

# NODES    
def build_context_node(state: GenerateState):
    content, source_context_text, embedded_text = build_content_inputs_lcver(
        docs=state["docs"],
        q=state["query"],
        cursor=state["cursor"]
    )
    return {
        "messages": [HumanMessage(content=content)],
        "user_message": HumanMessage(content=content)
    }
    
def strict_llm_generate_node(state: GenerateState):
    trimmed_messages = trim_messages(state["messages"], k=10)
    response = llm.invoke([
        SystemMessage(content=absenceBasedAbstain_system_prompt),
        *trimmed_messages
    ])  
    return {
        "raw_output": response.content,
        "pass_stage": "pass1",
        "retry_count": 0
    }

def parse_json_node(state: GenerateState):
    try:
        parsed = json.loads(state["raw_output"])
    except:
        parsed = None
    return {
        "parsed": parsed
    }  
    
def route_after_pass1(state: GenerateState):
    parsed = state["parsed"] 
    if parsed is None:
        return "repair1"
    if isinstance(parsed, list) and len(parsed)>0:
        return "end"
    return "pass2"     

def repair_pass1_node(state: GenerateState):
    answer = state["raw_output"]

    repair_prompt = f"""
                    The following text is invalid JSON.

                    Fix it into valid JSON.

                    TEXT:
                    {answer}
                    """

    response = llm.generate(
        system_prompt=JSON_FIX_PROMPT,
        content=[{"type": "input_text", "text": repair_prompt}]
    )

    return {
        "raw_output": response,
        "retry_count": state["retry_count"] + 1
    }

def route_after_repair1(state: GenerateState):
    if state["retry_count"] >= 3:
        return "pass2"

    return "parse1"

def route_after_pass2(state: GenerateState):
    if state["parsed"] is None:
        return "repair2"

    return "end"

def route_after_repair2(state: GenerateState):
    if state["retry_count"] >= 3:
        return "end"

    return "parse2"

def evidence_synthesis_llm_generate_node(state: GenerateState):
    trimmed_messages = trim_messages(state["messages"], k=10)
    response = llm.invoke([
        SystemMessage(content=evidenceBasedSynthesis_system_prompt),
        *trimmed_messages
    ])  
    return {
        "raw_output": response.content,
        "pass_stage": "pass2",
        "retry_count": 0
    }   
    
def repair_pass2_node(state: GenerateState):
    answer = state["raw_output"]

    repair_prompt = f"""
                    The following text is invalid JSON.

                    Fix it into valid JSON.

                    TEXT:
                    {answer}
                    """

    response = llm.generate(
        system_prompt=JSON_FIX_PROMPT,
        content=[{"type": "input_text", "text": repair_prompt}]
    )

    return {
        "raw_output": response,
        "retry_count": state["retry_count"] + 1
    }
    
def end_node(state: GenerateState):
    return state


# =========================================
# WIRING FULL GRAPH

# Node names
entry_build_context = "build_context"
pass1 = "pass1"
parse1 = "parse1"
repair1 = "repair1"

pass2 = "pass2"
parse2 = "parse2"
repair2 = "repair2"

end = "end"
# NODES
graph = StateGraph(GenerateState)

graph.add_node(entry_build_context, build_context_node)

graph.add_node(pass1, strict_llm_generate_node)
graph.add_node(parse1, parse_json_node)
graph.add_node(repair1, repair_pass1_node)

graph.add_node(pass2, evidence_synthesis_llm_generate_node)
graph.add_node(parse2, parse_json_node)
graph.add_node(repair2, repair_pass2_node)

graph.add_node(end, end_node)

# EDGES
# Entry
graph.set_entry_point(entry_build_context)
# Edges
graph.add_edge(entry_build_context, pass1)
graph.add_edge(pass1, parse1)
graph.add_conditional_edges(parse1, route_after_pass1, {
    "repair1": repair1,
    "pass2": pass2,
    "end": end
})
graph.add_conditional_edges(repair1, route_after_repair1, {
    "parse1": parse1,
    "pass2": pass2
})

graph.add_edge(pass2, parse2)
graph.add_conditional_edges(parse2, route_after_pass2, {
    "repair2": repair2,
    "end": end
})
graph.add_conditional_edges(repair2, route_after_repair2, {
    "parse2": parse2,
    "end": end
})

generate_graph = graph.compile()

    
# print(generate_app.get_graph().draw_mermaid())


# TEST ***************************************************
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

# query = "what is software engineering?"
# docs = multi_stages_retrieve(cursor=cursor, query=query)

# result = app.invoke({
#     "query": query,
#     "docs": docs,
#     "cursor": cursor
# })
# print(result)


