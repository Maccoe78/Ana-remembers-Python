import os
import tempfile
import whisper
from fastapi import UploadFile
from fastapi.responses import Response
from gtts import gTTS

# Laad Whisper model eenmalig bij opstarten
whisper_model = whisper.load_model("tiny")


async def speech_to_text(audio_bestand: UploadFile) -> str:
    """Ontvang een audiobestand en zet het om naar tekst via Whisper."""
    inhoud = await audio_bestand.read()

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(inhoud)
        tmp_pad = tmp.name

    try:
        resultaat = whisper_model.transcribe(tmp_pad, language="nl")
        tekst = resultaat["text"].strip()
    finally:
        os.unlink(tmp_pad)

    return tekst


def text_to_speech(tekst: str) -> Response:
    """Zet tekst om naar spraak via Google TTS en geef het terug als audio."""
    tts = gTTS(text=tekst, lang="nl")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tts.save(tmp.name)
        tmp_pad = tmp.name

    with open(tmp_pad, "rb") as f:
        audio_bytes = f.read()

    os.unlink(tmp_pad)

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=ana.mp3"},
    )
