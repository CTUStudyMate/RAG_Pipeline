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

def determine_intent(user_query: str):
    """Identify the user's intent from a predefined set of intents."""
    intent = rl(user_query)
    if not (intent.name) or (intent.similarity_score < 0.51):
        intent = 'need_retrieve'
    else:
        intent = intent.name    
    return intent    
    
    
    