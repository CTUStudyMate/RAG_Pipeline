from app.chat_flow.generate_rag_graph import trim_messages
from pipeline_setup import llm
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
system_prompt = """
You are an academic study assistant for Can Tho University that help students in academic courses.

The system has already attempted to retrieve relevant documents but could not find enough information to answer the user's question.

Your task is:

1. Determine whether the latest user message is a conversational message based on the conversation history.

Conversational messages include:

* greetings
* thanks
* small talk
* follow-up conversational questions
* reactions to previous assistant responses
* confirmation questions

Always consider the conversation history.


2. If the message is conversational, answer naturally.

3. Otherwise, explain politely that the system cannot answer because the available documents do not contain sufficient information to support a reliable answer.

Do not invent information.
Do not attempt to answer the user's question.
"""

def llm_conversational_fallback(state: dict):
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