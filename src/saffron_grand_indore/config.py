import os
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(
        "Missing OPENAI_API_KEY. Add it to a .env file in this project's root "
        "as OPENAI_API_KEY=your_key_here, then restart the server."
    )

CHATBOT_API_KEY = os.getenv("CHATBOT_API_KEY")  # the key your own clients must send

MODEL_NAME = "gpt-5-nano"
EMBED_MODEL = "text-embedding-3-small"
KNOWLEDGE_BASE_DIR = "knowledge_base"
DB_NAME = "vector_db"

SOURCE_RELEVANCE_MARGIN = 0.3
CANDIDATE_CEILING = 15
DOC_INCLUSION_MAX_DISTANCE = 1.1
CITATION_MAX_DISTANCE = 0.65
MAX_CONTEXT_CHARS = 12000
MAX_HISTORY_MESSAGES = 10