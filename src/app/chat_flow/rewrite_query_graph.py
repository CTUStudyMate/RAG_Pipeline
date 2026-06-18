from typing import Annotated, Sequence, TypedDict
from app.chat_flow.generate_rag_graph import trim_messages
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph
from pipeline_setup import llm
import re


class RewriteQueryState(TypedDict):
    messages: Sequence[BaseMessage]
    rewritten_query: str
    query: str | None


def sanitize_query(query: str) -> str:
    # remove quotes
    query = query.replace('"', ' ').replace("'", " ")

    # remove punctuation that breaks parser
    query = re.sub(r"[^\w\s]", " ", query)

    # collapse spaces
    query = re.sub(r"\s+", " ", query).strip()

    return query
    
def rewrite_query(state: RewriteQueryState):
    
    if not state.get("messages"):
        print("no messages")
        return {
            "rewritten_query": state["query"] if state.get("query") else None
        }

    recent_messages = trim_messages(state["messages"], k=10)

    chat_messages = (
        [
            SystemMessage(
                content=(
                    "Given the chat history, rewrite the new question "
                    "to be standalone and searchable. "
                    "Return ONLY the rewritten question."
                )
            )
        ]
        + recent_messages
        + [
            HumanMessage(
                content=f"New question: {state['query']}"
            )
        ]
    )

    result = llm.invoke(chat_messages)
    
    sanitized_query = sanitize_query(result.content)
    
    return {
        "rewritten_query": sanitized_query
    }

graph = StateGraph(RewriteQueryState)
graph.add_node("rewrite_query", rewrite_query)

graph.set_entry_point("rewrite_query")
graph.set_finish_point("rewrite_query")


rewrite_query_graph = graph.compile()    


## TEST   
# state: RewriteQueryState = {
#     "messages": [
#         HumanMessage(content="Hello"),
#         AIMessage(content="Hello. How can I help you?"),
#         HumanMessage(content="What is software engineering?"),
#         AIMessage(content="SE is the field of using SE knowledge for problem solving."),
#     ],
#     "rewritten_query": "",
#     "query": "And how does it fit into computer science?"
# }

# # state: RewriteQueryState = {
# #     "rewritten_query": "",
# #     "query": "And how does it fit into computer science?"
# # }

# rewrite_query_graph.invoke(state)

