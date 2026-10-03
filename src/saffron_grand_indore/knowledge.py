import os
import json

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import KNOWLEDGE_BASE_DIR, DB_NAME, EMBED_MODEL
from .documents import json_to_markdown

if not os.path.isdir(KNOWLEDGE_BASE_DIR):
    raise RuntimeError(
        f"Couldn't find the '{KNOWLEDGE_BASE_DIR}' folder. It should sit "
        "next to this project's root and contain your .md files plus "
        "saffron_grand_structured_data.json."
    )

prose_loader = DirectoryLoader(
    KNOWLEDGE_BASE_DIR, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"},
)
prose_docs = prose_loader.load()
for doc in prose_docs:
    filename = os.path.basename(doc.metadata["source"])
    doc.metadata["doctype"] = os.path.splitext(filename)[0]

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
prose_chunks = splitter.split_documents(prose_docs)

json_path = os.path.join(KNOWLEDGE_BASE_DIR, "saffron_grand_structured_data.json")
with open(json_path, "r", encoding="utf-8") as f:
    catalog_data = json.load(f)
catalog_docs = json_to_markdown(catalog_data)

all_chunks = catalog_docs + prose_chunks
embeddings = OpenAIEmbeddings(model=EMBED_MODEL)

if os.path.exists(DB_NAME):
    Chroma(persist_directory=DB_NAME, embedding_function=embeddings).delete_collection()

vectorstore = Chroma.from_documents(
    documents=all_chunks,
    embedding=embeddings,
    persist_directory=DB_NAME,
    collection_metadata={"hnsw:space": "cosine"},
)

ROOMS_BY_TYPE = {r["room_type"]: r for r in catalog_data.get("rooms", [])}
EXTRA_BED_CHARGE = catalog_data.get("policies", {}).get("extra_bed_charge_inr", 0)

print(f"Vectorstore built with {vectorstore._collection.count()} documents")
print(f"Indexed {len(ROOMS_BY_TYPE)} room type(s) for deterministic cost lookups")