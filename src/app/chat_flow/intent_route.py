from semantic_router import Route
from semantic_router.encoders import OpenAIEncoder
from semantic_router.routers import SemanticRouter
from pipeline_config import OPENAI_API_KEY
import json
from pipeline_setup import llm

# Semantic router set up
file_path = "src/app/chat_flow/routes_intent.json"
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

routes = [
    Route(name=r["name"], utterances=r["utterances"])
    for r in data["routes"]
]

encoder = OpenAIEncoder(openai_api_key=OPENAI_API_KEY)
rl = SemanticRouter(encoder=encoder, routes=routes, auto_sync="local")

ROUTE_NAMES = {route.name for route in routes}
VALID_INTENTS = ROUTE_NAMES | {"need_retrieve"}


def determine_intent_with_llm(user_query: str) -> str:
    """Use the LLM as a fallback when the semantic router is uncertain."""
    route_examples = "\n".join(
        f"- {route.name}: {', '.join(route.utterances)}"
        for route in routes
    )

    system_prompt = f"""
You are an intent classifier for a university assistant.

Classify the user's message into exactly one of the intents below.
Choose a route intent only when the message closely matches its examples.
Choose need_retrieve when the message asks for information or knowledge that
does not belong to any of the listed conversational intents.

Available intents and examples:
{route_examples}

Additional intent:
- need_retrieve: factual, academic, technical, or other information-seeking
  requests not covered by the routes above.

Return only the intent name. Do not add explanations, punctuation, Markdown,
or any other text.
"""

    try:
        result = llm.generate(
            system_prompt=system_prompt,
            content=user_query,
            reasoning_effort="minimal"
        )
        predicted_intent = result.strip().lower()
        predicted_intent = predicted_intent.strip("`'\" \n\t.,:")

        if predicted_intent in VALID_INTENTS:
            return predicted_intent
    except Exception as e:
        print(f"LLM intent classification failed: {e}")

    return "need_retrieve"


def determine_intent(user_query: str):
    """Identify the user's intent from a predefined set of intents."""
    user_query = user_query.lower().strip()
    intent = rl(user_query)
    if not (intent.name) or (intent.similarity_score < 0.51):
        print("Intent can't be defined by semantic router. Use LLM.")
        intent = determine_intent_with_llm(user_query)
    else:
        intent = intent.name    
    return intent    
    
    
    
