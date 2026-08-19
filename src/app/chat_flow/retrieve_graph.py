from PIPELINE._4_retrieve.multi_stages.multi_stages_retriever import multi_stages_retrieve
from langgraph.graph import StateGraph
from typing_extensions import TypedDict
from typing import Any

class RetrieveState(TypedDict):
    docs: list
    
    # external param
    rewritten_query: str
    document_sources: list[int] | None


def retrieve(state: RetrieveState):
    docs = multi_stages_retrieve(
        query=state["rewritten_query"],
        document_ids=state["document_sources"],
    )

    return {
        "docs": docs
    }


graph = StateGraph(RetrieveState)

graph.add_node("retrieve", retrieve)

graph.set_entry_point("retrieve")
graph.set_finish_point("retrieve")


retrieve_graph = graph.compile()
