from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field
from pipeline_setup import llm
from starlette.concurrency import run_in_threadpool
import re

class CuratedQa(BaseModel):
    question: str
    answer: str
class CuratedQaBatch(BaseModel):
    curated_qas: list[CuratedQa]    

CITATION_MARK_PATTERN = re.compile(r"\s*\[#citation\d+\]")

class TextVerifiedCitation(BaseModel):
    mark_number: int
    type: Literal["text"]
    doc_id: str
    evidences: list[str]


class ImageVerifiedCitation(BaseModel):
    mark_number: int
    type: Literal["image"]
    doc_id: str
    image_id: str


VerifiedCitation = Annotated[
    TextVerifiedCitation | ImageVerifiedCitation,
    Field(discriminator="type"),
]


class VerifiedAnswer(BaseModel):
    edited_answer: str
    citations: dict[str, VerifiedCitation]
    citation_map: dict[str, int]

class PendingQaCourse(BaseModel):
    course_id: int
    course_code: str
    course_name: str


class VerifiableQaGenerateRequest(BaseModel):
    verifiable_qa_id: int
    original_question: str
    rewritten_question: str | None = None
    generated_answer: str | None = None
    approved_answer: VerifiedAnswer
    created_at: datetime
    updated_at: datetime
    courses: list[PendingQaCourse]
    

# An empty curated-QA list is valid; the Main Backend handles it.
async def generate_curated_qas(vqa: VerifiableQaGenerateRequest):
    question = vqa.rewritten_question or vqa.original_question

    answer_obj = vqa.approved_answer
    raw_answer = answer_obj.edited_answer
    cleaned_answer = CITATION_MARK_PATTERN.sub("", raw_answer).strip()

    if not cleaned_answer:
        raise ValueError(
            "The verified QA has no approved answer after cutting off citation marks."
        )
        
    system_prompt = """
You are an expert at knowledge curation.

Your task is to transform one question-answer pair into multiple question-answer pairs using the following rules:
    0. Preserve Already-Atomic QA Pairs: First, determine whether the original QA pair already represents a single, coherent, and self-contained unit of knowledge. If it does, preserve it as one curated QA pair and do not split it unnecessarily. Only decompose the original pair when it contains multiple distinct information needs or independently reusable knowledge units.
    1. Single Information Need: Each question should ask about only one primary definition, attribute, relationship, cause, purpose, step, or condition.
    2. Semantic Cohesion: Statements that directly explain the same information need should be kept together. Statements that answer a different information need should be separated into another QA pair.
    3. Self-Containedness: Each question and answer must be understandable on its own and should not rely on ambiguous pronouns or unclear references.
    4. Source Faithfulness: All information in the answer must be directly supported by the original QA pair or its underlying source. Do not introduce facts that are absent from the supplied question and answer.
    5. Sufficient Context: Do not split the content so narrowly that essential information, such as the subject, relationship, purpose, or condition, is lost.
    6. Minimal Redundancy: Do not create multiple curated QA pairs that have the same intent and nearly identical answers.
    7. Meaning Preservation: Preserve the original level of certainty, conditions, exceptions, and scope of the source content.
    8. Reusability: Keep only QA pairs that are meaningful, retrievable, and usable independently in future contexts.

Example:
    Input: 
        Question:
        What is software engineering and how does it fit into computer science?

        Answer:
        Software engineering is the use of knowledge of computers and computing
        to help solve problems, often related to computer systems, by first
        understanding the nature of the problem and then using technology as a
        tool to implement a solution if necessary.

        Software engineers use tools, techniques, procedures, and paradigms to
        enhance the quality of their software products, aiming to use efficient
        and productive approaches to generate effective solutions to problems.

        Software engineering can be considered as a subfield of computer science.
    Output: 
        {
            "curated_qas": [
                {
                    "question": "What is software engineering?",
                    "answer": "Software engineering is the use of knowledge of computers and computing to help solve problems, often related to computer systems, by first understanding the nature of the problem and then using technology as a tool to implement a solution if necessary. Software engineers use tools, techniques, procedures, and paradigms to enhance the quality of their software products and generate effective solutions to problems."
                },
                {
                    "question": "How does software engineering fit into computer science?",
                    "answer": "Software engineering can be considered a subfield of computer science."
                }
            ] 
        }
            

Now, transform the question-answer pair below:  
    """
    
    content = f"""
Question: {question}

Answer: {cleaned_answer}
"""
    

    response = await run_in_threadpool(
        llm.client.responses.parse,
        model=llm.model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        text_format=CuratedQaBatch,
    )
    
    result: CuratedQaBatch | None = response.output_parsed
    if result is None:
        raise ValueError("The LLM returned no structured output.")

    return result
