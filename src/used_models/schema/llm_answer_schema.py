# this was just code for only openai provider, the code for other providers have not been support now
from pydantic import BaseModel, Field
from typing import List


class Segment(BaseModel):
    text: str = Field(
        description=(
            "A factual claim that is an exact quote copied verbatim from the final answer. "
        )
    )

    sources: List[int] = Field(
        description=(
            "Indices of the retrieved context documents that provide information for the claim."
        )
    )


class AnswerSchema(BaseModel):
    answer: str = Field(
        description=(
            "A coherent final answer. "
        )
    )

    segments: List[Segment] = Field(
        description=(
            "A list of factual claim spans extracted directly from the final answer. "
            "Each segment.text must be an exact substring copied from the answer field."
        )
    )