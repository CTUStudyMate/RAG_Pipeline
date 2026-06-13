from app.chat_flow.intent_route import determine_intent
from langgraph.graph import StateGraph
from typing_extensions import TypedDict

class IntentRouteGraph(TypedDict):
    query: str
    intent: str

def get_user_intent(state: IntentRouteGraph):
    intent = determine_intent(user_query=state["query"])
    return {
        "intent": intent
    } 

graph = StateGraph(IntentRouteGraph)

graph.add_node("intent", get_user_intent)

graph.set_entry_point("intent")
graph.set_finish_point("intent")


intent_graph = graph.compile()    