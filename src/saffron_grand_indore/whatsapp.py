"""
WhatsApp Cloud API front door for the Hotel Concierge Bot.

Usage in main.py (2 lines):

    from whatsapp import create_whatsapp_router
    app.include_router(create_whatsapp_router(answer_question))

Assumes answer_question(question: str, history: list[dict]) -> str
(sync or async). `history` is a list like [{"role": "user", "content": "..."},
{"role": "assistant", "content": "..."}], oldest first, NOT including the
current question. If your function has a different signature, change the
single call inside `_get_answer` below.

Render environment variables:
    WHATSAPP_TOKEN         access token (temporary for testing, system-user token for live)
    WHATSAPP_PHONE_ID      Phone Number ID from API Setup
    WHATSAPP_VERIFY_TOKEN  any long random string; paste the same into Meta's webhook form
    WHATSAPP_APP_SECRET    (recommended) App settings > Basic > App secret
    WHATSAPP_GRAPH_VERSION (optional) defaults to v23.0

Needs: pip install httpx   (add to requirements.txt)
"""

import hashlib
import hmac
import inspect
import json
import logging
import os
from collections import OrderedDict, defaultdict, deque

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse

log = logging.getLogger("whatsapp")

HISTORY_TURNS = 8          # past messages remembered per guest (user + assistant)
SEEN_IDS_MAX = 2000        # recent message ids kept to ignore Meta retries
WA_MAX_CHARS = 4000        # WhatsApp text limit is 4096


def create_whatsapp_router(answer_question) -> APIRouter:
    router = APIRouter()

    # --- simple in-memory stores (reset on restart; swap for Supabase later) ---
    histories: dict[str, deque] = defaultdict(lambda: deque(maxlen=HISTORY_TURNS))
    seen_ids: "OrderedDict[str, None]" = OrderedDict()

    def _env(name: str, default: str = "") -> str:
        return os.environ.get(name, default)

    # ------------------------------------------------------------------ #
    # 1) Meta's one-time webhook verification
    # ------------------------------------------------------------------ #
    @router.get("/whatsapp")
    async def verify(
        hub_mode: str = Query(None, alias="hub.mode"),
        hub_token: str = Query(None, alias="hub.verify_token"),
        hub_challenge: str = Query(None, alias="hub.challenge"),
    ):
        expected = _env("WHATSAPP_VERIFY_TOKEN")
        if hub_mode == "subscribe" and expected and hmac.compare_digest(hub_token or "", expected):
            return PlainTextResponse(hub_challenge or "")
        raise HTTPException(status_code=403, detail="invalid verify token")

    # ------------------------------------------------------------------ #
    # 2) Incoming messages
    # ------------------------------------------------------------------ #
    @router.post("/whatsapp")
    async def receive(request: Request, background: BackgroundTasks):
        raw = await request.body()

        # Optional but recommended: confirm the request really came from Meta
        secret = _env("WHATSAPP_APP_SECRET")
        if secret:
            sent = request.headers.get("X-Hub-Signature-256", "")
            good = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sent, good):
                raise HTTPException(status_code=403, detail="bad signature")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"status": "ignored"}

        # Meta sends many event types (delivery/read receipts etc). Pull out real messages only.
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []) or []:
                    msg_id = msg.get("id")
                    if msg_id in seen_ids:          # Meta retried; already handled
                        continue
                    if msg_id:
                        seen_ids[msg_id] = None
                        while len(seen_ids) > SEEN_IDS_MAX:
                            seen_ids.popitem(last=False)

                    sender = msg.get("from")
                    if not sender:
                        continue
                    if msg.get("type") == "text":
                        text = (msg.get("text") or {}).get("body", "").strip()
                    else:
                        text = ""
                    background.add_task(_handle, sender, text)

        # Return 200 straight away so Meta doesn't retry while we think
        return {"status": "ok"}

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    async def _get_answer(question: str, history: list) -> str:
        # >>> If your answer_question signature differs, edit this call <<<
        if inspect.iscoroutinefunction(answer_question):
            result = await answer_question(question, history)
        else:
            result = await run_in_threadpool(answer_question, question, history)
        return result if isinstance(result, str) else str(result)

    async def _handle(sender: str, text: str):
        try:
            if not text:
                await _send(sender, "Sorry, I can only read text messages right now. Could you type your question?")
                return

            history = list(histories[sender])
            reply = await _get_answer(text, history)

            histories[sender].append({"role": "user", "content": text})
            histories[sender].append({"role": "assistant", "content": reply})
            await _send(sender, reply)
        except Exception:
            log.exception("failed handling WhatsApp message from %s", sender)
            try:
                await _send(sender, "Sorry, something went wrong on our side. Please try again in a moment.")
            except Exception:
                log.exception("also failed to send the error reply")

    async def _send(to: str, body: str):
        token = _env("WHATSAPP_TOKEN")
        phone_id = _env("WHATSAPP_PHONE_ID")
        version = _env("WHATSAPP_GRAPH_VERSION", "v23.0")
        url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body[:WA_MAX_CHARS]},
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json=data, headers={"Authorization": f"Bearer {token}"})
        if r.status_code >= 300:
            log.error("WhatsApp send failed %s: %s", r.status_code, r.text)

    return router
