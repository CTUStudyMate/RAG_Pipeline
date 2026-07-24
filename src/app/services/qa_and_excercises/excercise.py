from pydantic import BaseModel, Field
from pipeline_setup import llm
from starlette.concurrency import run_in_threadpool


class CuratedQaToRagEngine(BaseModel):
    curated_qa_id: int = Field(alias="curated_qa_id")
    question: str
    answer: str
    course_names: list[str] = Field(
        default_factory=list,
        alias="course_names",
    )


class GeneratedMcqResponse(BaseModel):
    question: str
    choices: list[str] = Field(default_factory=list)
    correct_choice_index: int = Field(alias="correctChoiceIndex")
    explanation: str


class GeneratedFillBlankResponse(BaseModel):
    text: str
    accepted_answers: list[str] = Field(
        default_factory=list,
        alias="acceptedAnswers",
    )
    explanation: str


class GeneratedMatchingPairResponse(BaseModel):
    left: str
    right: str
    relation: str


class GenerateExercisesResponse(BaseModel):
    mcq: GeneratedMcqResponse
    fill_blank: GeneratedFillBlankResponse = Field(alias="fillBlank")
    matching_pair: GeneratedMatchingPairResponse = Field(alias="matchingPair")


async def generate_exercises(
    curated_qa: CuratedQaToRagEngine,
) -> GenerateExercisesResponse:
    question = curated_qa.question.strip()
    answer = curated_qa.answer.strip()

    if not question or not answer:
        raise ValueError(
            "The request must include a non-empty curated question and answer."
        )

    course_context = ", ".join(curated_qa.course_names) or "Not provided"

    system_prompt = """
You generate high-quality learning exercises from a single curated question-and-answer pair.

Use only facts explicitly stated or directly implied by the provided source question and answer. Do not add external knowledge, assumptions, examples, or facts.

Return exactly one valid JSON object. Do not include Markdown, code fences, comments, or any text before or after the JSON.

The JSON must follow this exact schema:

{
  "mcq": {
    "question": "string",
    "choices": ["string", "string", "string", "string"],
    "correctChoiceIndex": 0,
    "explanation": "string"
  },
  "fillBlank": {
    "text": "string with exactly one ___ placeholder",
    "acceptedAnswers": ["string"],
    "explanation": "string"
  },
  "matchingPair": {
    "left": "string",
    "right": "string",
    "relation": "string"
  }
}

Requirements for all exercises:
- Each exercise must assess one clear learning point only.
- Use the same language as the source question and answer.
- Ensure statements are clear, self-contained, grammatically correct, and factually supported by the source.
- Generate all three exercise types. Do not use null values.

Requirements for "mcq":
- "question" must be a clear, self-contained question.
- "choices" must contain exactly four non-empty choices.
- Exactly one choice must be correct.
- "correctChoiceIndex" must be an integer from 0 to 3 and point to the correct item in "choices".
- All choices must have a similar grammatical form and semantic category.
- Incorrect choices must be plausible but clearly incorrect according to the source.
- Do not use duplicate or semantically equivalent choices.
- Do not reveal the correct answer through noticeably different grammar, wording, specificity, or length.
- "explanation" must explain why the selected choice is correct using only the source information.

Requirements for "fillBlank":
- "text" must be a complete statement containing exactly one ___ placeholder.
- The blank must represent an important concept, term, fact, or relationship from the source.
- Keep the missing answer concise; do not make the blank unnecessarily long.
- "acceptedAnswers" must contain one or more valid answers that correctly complete the blank.
- "explanation" must explain the completed statement using only the source information.

Requirements for "matchingPair":
- "left" must be a concise term, concept, entity, process, category, cause, or component from the source.
- "right" must be its corresponding definition, function, property, purpose, effect, result, or category relationship.
- "relation" must be exactly one of:
  "TermDefinition",
  "ComponentFunction",
  "EntityProperty",
  "MethodPurpose",
  "CauseEffect",
  "ProcessResult",
  "CategoryMember".
- Choose the relation value that best describes the relationship between "left" and "right".
"""

    user_prompt = f"""
Generate exercises from the following curated question-answer pair.

Course context: {course_context}

Source question:
{question}

Source answer:
{answer}
"""

    try:
        response = await run_in_threadpool(
            llm.client.responses.parse,
            model=llm.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=GenerateExercisesResponse,
        )
    except Exception as exc:
        raise RuntimeError(
            "Failed to generate exercises from the curated QA pair."
        ) from exc

    result: GenerateExercisesResponse | None = response.output_parsed
    if result is None:
        raise ValueError("The LLM returned no structured exercise output.")

    return result
