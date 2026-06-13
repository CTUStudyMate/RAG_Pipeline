from used_models.llm.LLM_Factory import get_llm
from pipeline_config import settings

llm = get_llm(provider=settings.config["llm_provider"])
model = llm.lcModel