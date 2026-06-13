from semantic_router import Route
import os
from semantic_router.encoders import OpenAIEncoder
from semantic_router.routers import SemanticRouter
from pipeline_config import OPENAI_API_KEY

normal_conversation = Route(
    name="normal_conversation",
    utterances=[
        # greetings
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",

        # small talk
        "how are you",
        "how's it going",
        "what's up",
        "how have you been",

        # casual interaction
        "tell me a joke",
        "make me laugh",
        "say something funny",
        "can we chat",

        # politeness / acknowledgements
        "thanks",
        "thank you",
        "ok",
        "got it",
        "sounds good",
        "nice",

        # emotional feedback
        "that's nice",
        "cool",
        "awesome",
        "great"
    ]
)

chatbot_meta = Route(
    name="chatbot_meta",
    utterances=[
        # identity
        "who are you",
        "what are you",
        "tell me about yourself",

        # capability
        "what can you do",
        "what are your capabilities",
        "how can you help me",
        "what are you used for",

        # system behavior
        "how do you work",
        "how does this chatbot work",
        "are you using AI",
        "are you a language model",

        # scope
        "what topics can you answer",
        "what can you not answer",
        "what data do you use",

        # RAG / knowledge system (important for thesis!)
        "do you use documents",
        "do you search the database",
        "how do you retrieve information",
        "where do your answers come from"
    ]
)

need_retrieve = Route(
    name="need_retrieve",
    utterances=[
        # academic / explanation
        "explain transformer architecture",
        "what is machine learning",
        "define convolutional neural network",

        # factual QA
        "what is the main idea of lecture 3",
        "summarize the document",
        "what does this paper say",

        # procedural knowledge
        "how does backpropagation work",
        "steps of gradient descent",
        "how to implement bfs",

        # document-based questions
        "according to the lecture notes",
        "based on the document",
        "from the slides",
        "in the material provided",

        # generic question forms
        "what is ...",
        "why does ...",
        "how does ...",
        "explain ...",
        "describe ...",
        "summarize ...",
        "list ...",
        "compare ...",
        "difference between ...",

        # implicit retrieval triggers
        "can you explain this topic",
        "help me understand this concept",
        "I need details about this subject"
    ]
)

# we place both of our decisions together into single list
routes = [normal_conversation, chatbot_meta, need_retrieve]
encoder = OpenAIEncoder(openai_api_key=OPENAI_API_KEY)
rl = SemanticRouter(encoder=encoder, routes=routes, auto_sync="local")
type = rl("Hello, I am a new student")
print(type)