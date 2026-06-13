from PIPELINE._6_citation_postprocessing.validate_citation import filter_segments
from langgraph.graph import StateGraph
from typing_extensions import TypedDict

class CiteState(TypedDict):
    segments: list
    docs: list

def validate_answer_citation_node(state: CiteState):
    valid_segments = filter_segments(
        segments=state["segments"],
        context_chunks=state["docs"]
    )
    
    return {
        "segments": valid_segments
    }


graph = StateGraph(CiteState)

graph.add_node("validate_citation", validate_answer_citation_node)

graph.set_entry_point("validate_citation")
graph.set_finish_point("validate_citation")

validate_graph = graph.compile()