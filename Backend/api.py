import os
import uuid
import ollama
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from patient_manager import (
    patient_bestaat, nieuwe_patient, laad_patient, sla_patient_op,
    voeg_sessie_toe, maak_geheugen_samenvatting
)
from escalatie import analyseer_symptomen, check_escalatie
from embeddings import vind_symptoom

app = FastAPI(title="Ana Health Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_NAAM = "llama3.1:8b"

# In-memory session store: session_id -> { patient, geschiedenis }
actieve_sessies: dict = {}


class BerichtRequest(BaseModel):
    bericht: str


# ------------------------------------------------------------------
# Patienten
# ------------------------------------------------------------------

@app.get("/patients")
def lijst_patienten():
    """Geef een lijst van alle patiëntnamen terug."""
    map_naam = "patient_data"
    if not os.path.exists(map_naam):
        return []
    bestanden = [b for b in os.listdir(map_naam) if b.endswith(".json")]
    return [b.replace(".json", "") for b in bestanden]


@app.get("/patients/{naam}")
def get_patient(naam: str):
    """Haal patiëntgegevens op zonder volledige berichtenhistorie."""
    if not patient_bestaat(naam):
        raise HTTPException(status_code=404, detail="Patient niet gevonden")
    patient = laad_patient(naam)
    return {
        "naam": patient["naam"],
        "medicijnen": patient["medicijnen"],
        "sessies": [
            {
                "datum": s["datum"],
                "aantal_berichten": len([b for b in s["berichten"] if b["role"] == "user"]),
            }
            for s in patient["sessies"]
        ],
    }


@app.post("/patients/{naam}/session/start")
def start_sessie(naam: str):
    """
    Start een nieuwe check-in sessie voor een patiënt.
    Geeft een session_id en de openingsboodschap van Ana terug.
    """
    if patient_bestaat(naam):
        patient = laad_patient(naam)
        is_nieuw = False
    else:
        patient = nieuwe_patient(naam)
        is_nieuw = True

    geheugen = maak_geheugen_samenvatting(patient)

    geschiedenis = [
        {
            "role": "system",
            "content": (
                "Jij bent Ana, een vriendelijke zorgassistent voor hartfalen patienten. "
                "De patient heet " + naam + ". "
                "Stel vragen over: kortademigheid, enkelbezwelling, gewicht, en medicijnen. "
                "Stel elke keer maar een vraag. "
                "Als je kortademigheid, enkelzwelling, gewicht en medicijnen hebt besproken, "
                "sluit je het gesprek vriendelijk af en schrijf je op de laatste regel precies: [GESPREK_KLAAR] "
                "Verwijs naar eerdere gesprekken als dat relevant is. "
                "\n\n" + geheugen
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
        "patient": patient,
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

    gesprek_klaar = "[GESPREK_KLAAR]" in ana_tekst
    if gesprek_klaar:
        ana_tekst = ana_tekst.replace("[GESPREK_KLAAR]", "").strip()

    geschiedenis.append({"role": "assistant", "content": ana_tekst})

    return {
        "ana_bericht": ana_tekst,
        "gesprek_klaar": gesprek_klaar,
        "herkend_symptoom": gevonden_symptoom,
    }


@app.post("/patients/{naam}/session/{session_id}/end")
def beeindig_sessie(naam: str, session_id: str):
    
    if session_id not in actieve_sessies:
        raise HTTPException(status_code=404, detail="Sessie niet gevonden")

    sessie = actieve_sessies.pop(session_id)
    patient = sessie["patient"]
    geschiedenis = sessie["geschiedenis"]

    voeg_sessie_toe(patient, geschiedenis)

    analyse = analyseer_symptomen(geschiedenis)
    niveau, reden = check_escalatie(analyse)

    sla_patient_op(patient)

    return {
        "escalatie_niveau": niveau,
        "reden": reden,
        "analyse_tekst": analyse,
    }
