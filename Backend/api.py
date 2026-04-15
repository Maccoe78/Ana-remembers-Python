import uuid
import ollama
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from database import (
    patient_bestaat, nieuwe_patient, laad_patient,
    maak_geheugen_samenvatting, sla_sessie_op, haal_sessies_op,
    get_verbinding
)
from escalatie import analyseer_symptomen, check_escalatie, genereer_samenvatting
from embeddings import vind_symptoom
from voice import speech_to_text, text_to_speech

app = FastAPI(title="Ana Health Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_NAAM = "llama3.1:8b"

# In-memory session store: session_id -> { patient_naam, geschiedenis }
actieve_sessies: dict = {}


class BerichtRequest(BaseModel):
    bericht: str


def parse_analyse(analyse_tekst: str) -> dict:
    """Zet de tekstuele analyse van Ollama om naar een gestructureerd dict."""
    result = {}
    for lijn in analyse_tekst.lower().splitlines():
        if "kortademigheid:" in lijn:
            result["kortademigheid"] = lijn.split(":", 1)[1].strip()
        elif "enkelbew" in lijn and ":" in lijn:
            result["enkelbezwelling"] = lijn.split(":", 1)[1].strip()
        elif lijn.startswith("trend:"):
            result["trend"] = lijn.split(":", 1)[1].strip()
    return result


# ------------------------------------------------------------------
# Patienten
# ------------------------------------------------------------------

@app.get("/patients")
def lijst_patienten():
    """Geef een lijst van alle patiëntnamen terug."""
    with get_verbinding() as db:
        rijen = db.execute("SELECT naam FROM patienten").fetchall()
    return [r["naam"] for r in rijen]


@app.get("/patients/{naam}")
def get_patient(naam: str):
    """Haal patiëntgegevens en sessie-overzicht op."""
    if not patient_bestaat(naam):
        raise HTTPException(status_code=404, detail="Patient niet gevonden")
    patient = laad_patient(naam)
    sessies = haal_sessies_op(naam)
    return {
        "naam": patient["naam"],
        "medicijnen": patient["medicijnen"],
        "sessies": sessies,
    }


# ------------------------------------------------------------------
# Sessie beheer
# ------------------------------------------------------------------

@app.post("/patients/{naam}/session/start")
def start_sessie(naam: str):
    """Start een nieuwe check-in sessie voor een patiënt."""
    if not patient_bestaat(naam):
        nieuwe_patient(naam)

    sessies = haal_sessies_op(naam)
    is_nieuw = len(sessies) == 0

    geheugen = maak_geheugen_samenvatting(naam)

    if is_nieuw:
        geheugen_instructie = (
            "BELANGRIJK: Dit is de ALLEREERSTE keer dat je deze patient spreekt. "
            "Er zijn GEEN eerdere gesprekken. Zeg NOOIT dingen zoals 'sinds de vorige keer' "
            "of 'de laatste keer dat we spraken'. Stel jezelf voor als Ana."
        )
    else:
        geheugen_instructie = (
            "Verwijs naar eerdere gesprekken als dat relevant is. "
            "Gebruik ALLEEN informatie die expliciet in de vorige sessies staat hieronder, verzin niets. "
            "\n\n" + geheugen
        )

    geschiedenis = [
        {
            "role": "system",
            "content": (
                "Jij bent Ana, een warme en vriendelijke zorgassistent voor hartfalen patienten. "
                "De patient heet " + naam + ". "
                "Vraag niet naar wat hij in de ochtend heeft gedaan of hoe de nacht was, maar focus op hoe hij zich NU voelt en de symptomen die hij NU ervaart. "
                "VERBODEN: verzin geen eerdere gesprekken, stel geen vragen over andere medische onderwerpen, "
                "Doe een check-in gesprek zoals een zorgzame verpleegster dat zou doen. "
                "Stel jezelf voor, vraag hoe de patient zich voelt, en bespreek dan deze 4 onderwerpen: "
                "kortademigheid, zwelling in enkels of benen, gewicht, en medicijnen. "
                "Stel EEN vraag per keer en wacht op het antwoord voordat je verdergaat. "
                "Reageer kort en empathisch op elk antwoord voordat je de volgende vraag stelt. "
                "doe geen lichamelijk onderzoek voor, en maak geen beloftes die je niet kunt nakomen. "
                "Als alle 4 onderwerpen besproken zijn, sluit vriendelijk af met een korte samenvatting "
                "en schrijf op de LAATSTE REGEL ALLEEN: GESPREK_KLAAR\n"
                "\n\n" + geheugen_instructie
            ),
        }
    ]

    eerste_bericht = ollama.chat(
        model=MODEL_NAAM,
        messages=geschiedenis + [{"role": "user", "content": "Start de check-in"}],
    )
    eerste_tekst = eerste_bericht["message"]["content"]
    geschiedenis.append({"role": "assistant", "content": eerste_tekst})

    session_id = str(uuid.uuid4())
    actieve_sessies[session_id] = {
        "patient_naam": naam.lower().strip(),
        "geschiedenis": geschiedenis,
    }

    return {
        "session_id": session_id,
        "is_nieuw": is_nieuw,
        "ana_bericht": eerste_tekst,
        "gesprek_klaar": False,
    }


@app.post("/patients/{naam}/session/{session_id}/message")
def stuur_bericht(naam: str, session_id: str, body: BerichtRequest):
    """Stuur een bericht naar Ana en ontvang haar antwoord."""
    if session_id not in actieve_sessies:
        raise HTTPException(status_code=404, detail="Sessie niet gevonden")

    sessie = actieve_sessies[session_id]
    geschiedenis = sessie["geschiedenis"]

    geschiedenis.append({"role": "user", "content": body.bericht})

    # Embedding check: herken indirect genoemde symptomen
    gevonden_symptoom = vind_symptoom(body.bericht)
    berichten_voor_ollama = geschiedenis.copy()
    if gevonden_symptoom:
        berichten_voor_ollama.append({
            "role": "user",
            "content": (
                f"[SYSTEEM HINT: op basis van wat ik zei lijkt er sprake te zijn van '{gevonden_symptoom}'. "
                f"Benoem dit voorzichtig en vraag er op door. Reageer alleen als Ana, niet op deze hint zelf.]"
            )
        })

    antwoord = ollama.chat(model=MODEL_NAAM, messages=berichten_voor_ollama)
    ana_tekst = antwoord["message"]["content"]

    gesprek_klaar = "[GESPREK_KLAAR]" in ana_tekst or "GESPREK_KLAAR" in ana_tekst
    if gesprek_klaar:
        ana_tekst = ana_tekst.replace("[GESPREK_KLAAR]", "").replace("GESPREK_KLAAR", "").strip()

    geschiedenis.append({"role": "assistant", "content": ana_tekst})

    return {
        "ana_bericht": ana_tekst,
        "gesprek_klaar": gesprek_klaar,
        "herkend_symptoom": gevonden_symptoom,
    }


@app.post("/patients/{naam}/session/{session_id}/end")
def beeindig_sessie(naam: str, session_id: str):
    """Beëindig de sessie, analyseer symptomen en sla op in de database."""
    if session_id not in actieve_sessies:
        raise HTTPException(status_code=404, detail="Sessie niet gevonden")

    sessie = actieve_sessies.pop(session_id)
    patient_naam = sessie["patient_naam"]
    geschiedenis = sessie["geschiedenis"]

    # Analyseer het gesprek
    analyse_tekst = analyseer_symptomen(geschiedenis)
    niveau, reden = check_escalatie(analyse_tekst)

    # Zet de analyse tekst om naar gestructureerd dict
    analyse = parse_analyse(analyse_tekst)
    analyse["escalatie_niveau"] = niveau
    analyse["reden"] = reden
    analyse["samenvatting"] = genereer_samenvatting(geschiedenis)

    # Sla op in de database
    sla_sessie_op(patient_naam, geschiedenis, analyse)

    return {
        "escalatie_niveau": niveau,
        "reden": reden,
        "analyse_tekst": analyse_tekst,
    }


# ------------------------------------------------------------------
# Stem endpoints
# ------------------------------------------------------------------

@app.post("/speech-to-text")
async def stt_endpoint(audio: UploadFile = File(...)):
    """Ontvang een audiobestand en geef de getranscribeerde tekst terug."""
    tekst = await speech_to_text(audio)
    return {"tekst": tekst}


@app.post("/text-to-speech")
async def tts_endpoint(body: BerichtRequest):
    """Ontvang tekst en geef een audiobestand terug."""
    return text_to_speech(body.bericht)
