"""WhatsApp Cloud API webhook for the Saffron Grand concierge.

Meta calls GET /whatsapp once to verify the webhook, then POSTs every incoming
guest message to /whatsapp. We answer with the same answer_question() brain the
website widget uses, and send the reply back through Meta's Graph API.
"""
import hashlib
import hmac
import os
import re
from collections import OrderedDict

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from .chat import answer_question

router = APIRouter()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")  # optional but recommended
API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v23.0")

MAX_TURNS_KEPT = 20          # messages remembered per guest
MAX_GUESTS_KEPT = 500        # guests remembered at once (oldest dropped first)
MAX_SEEN_IDS = 2000          # message ids remembered, to ignore Meta retries
WHATSAPP_TEXT_LIMIT = 4000   # WhatsApp allows 4096 characters per text message

# In-memory only: this resets whenever the server restarts or sleeps.
# For real clients, move it to a database (e.g. Supabase) keyed by phone number.
_histories = OrderedDict()   # phone number -> [{"role": ..., "content": ...}]
_seen_ids = OrderedDict()    # message id -> True


def _remember_guest(phone):
    history = _histories.setdefault(phone, [])
    _histories.move_to_end(phone)
    while len(_histories) > MAX_GUESTS_KEPT:
        _histories.popitem(last=False)
    return history


def _already_handled(message_id):
    if message_id in _seen_ids:
        return True
    _seen_ids[message_id] = True
    while len(_seen_ids) > MAX_SEEN_IDS:
        _seen_ids.popitem(last=False)
    return False


def to_whatsapp_format(text):
    """WhatsApp bolds with *one* asterisk; the model writes **two**."""
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    return text[:WHATSAPP_TEXT_LIMIT]


def send_text(to, body):
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code >= 400:
            print(f"WhatsApp send failed ({resp.status_code}): {resp.text}")
    except httpx.HTTPError as err:
        print(f"WhatsApp send error: {err}")


def handle_guest_message(phone, text):
    history = _remember_guest(phone)
    try:
        answer = answer_question(text, list(history))
    except Exception as err:  # never let one bad message kill the worker
        print(f"answer_question failed: {err}")
        answer = (
            "Sorry, I'm having trouble right now. "
            "Please try again in a moment."
        )
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": answer})
    del history[:-MAX_TURNS_KEPT]
    send_text(phone, to_whatsapp_format(answer))


def _signature_ok(raw_body, header):
    if not APP_SECRET:
        return True  # signature check not configured
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.split("=", 1)[1])


@router.get("/whatsapp")
def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    if mode == "subscribe" and VERIFY_TOKEN and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge or "")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def receive_message(request: Request, background: BackgroundTasks):
    raw_body = await request.body()
    if not _signature_ok(raw_body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="Bad signature")

    try:
        data = await request.json()
    except ValueError:
        return {"status": "ignored"}

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                if _already_handled(msg.get("id")):
                    continue
                phone = msg.get("from")
                if msg.get("type") == "text":
                    text = msg["text"]["body"].strip()
                    if phone and text:
                        background.add_task(handle_guest_message, phone, text)
                elif phone:
                    background.add_task(
                        send_text,
                        phone,
                        "Sorry, I can only read text messages for now. "
                        "Please type your question.",
                    )

    # Meta needs a fast 200, otherwise it retries the same message.
    return {"status": "ok"}