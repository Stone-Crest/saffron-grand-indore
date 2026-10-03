from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from .chat import answer_question
from .config import CHATBOT_API_KEY

app = FastAPI(title="Saffron Grand Concierge API")


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: Optional[List[ChatTurn]] = []


class ChatResponse(BaseModel):
    answer: str


def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if CHATBOT_API_KEY and x_api_key != CHATBOT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    history = [turn.model_dump() for turn in request.history]
    answer = answer_question(request.question, history)
    return ChatResponse(answer=answer)