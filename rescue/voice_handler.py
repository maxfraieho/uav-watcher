"""
Voice message transcription via Groq Whisper API.
Transcribed text is passed to Sharon consultant as if typed by the user.
Use case: user with injured hands — one tap to record, Sharon responds.
"""
import logging
import httpx

log = logging.getLogger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
_MODEL = "whisper-large-v3-turbo"


async def _transcribe(audio_bytes: bytes, api_key: str) -> str:
    """Send audio to Groq Whisper, return transcribed text."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("voice.ogg", audio_bytes, "audio/ogg")},
            data={"model": _MODEL, "language": "uk", "response_format": "text"},
        )
        resp.raise_for_status()
        return resp.text.strip()


async def _ask_sharon(text: str, user_id: int) -> str:
    """Forward transcribed text to Sharon consultant."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "http://localhost:8770/chat",
            json={"message": text, "session_id": str(user_id)},
        )
        resp.raise_for_status()
        return resp.json().get("reply", "")


def register_voice_handlers(bot_client, cfg):
    """Register voice message handler on the bot client."""
    from telethon import events

    api_key = cfg.get("groq_api_key", "")
    if not api_key:
        log.warning("groq_api_key not in config — voice transcription disabled")
        return

    @bot_client.on(events.NewMessage(func=lambda e: e.voice is not None))
    async def handle_voice(event):
        await event.respond("🎤 Розпізнаю голос...")
        try:
            audio_bytes = await event.download_media(bytes)
            text = await _transcribe(audio_bytes, api_key)
        except Exception as e:
            log.error(f"Groq transcription error: {e}")
            await event.respond("Не вдалося розпізнати. Спробуй ще або напиши текстом.")
            return

        if not text:
            await event.respond("Голос не розпізнано. Спробуй ще раз.")
            return

        await event.respond(f"🎤 _{text}_", parse_mode="md")

        try:
            sender = await event.get_sender()
            reply = await _ask_sharon(text, sender.id)
            if reply:
                await event.respond(reply)
        except Exception as e:
            log.error(f"Sharon request error after voice: {e}")

    log.info("Voice transcription handler registered (Groq Whisper).")
