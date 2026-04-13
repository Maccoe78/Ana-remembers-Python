import ollama
import numpy as np

# Bekende symptomen met beschrijvingen in natuurlijke taal
# Hoe meer beschrijvingen, hoe beter de herkenning
SYMPTOMEN = {
    "hoge_bloeddruk": (
        "hart klopt snel en hard, bonzend hoofd, druk op de borst, "
        "verhoogde hartslag, pols voelen, hartkloppingen, hart bonkt"
    ),
    "kortademigheid": (
        "moeite met ademen, buiten adem, zwaar ademen, niet genoeg lucht, "
        "benauwd, kortademig, hijgen, moeilijk ademen bij trap lopen"
    ),
    "enkelbezwelling": (
        "dikke enkels, gezwollen benen, voeten opgezet, enkels dik, "
        "vocht in de benen, broek past niet meer, schoenen knellen"
    ),
    "vermoeidheid": (
        "erg moe, uitgeput, geen energie, slap, kan niet veel doen, "
        "snel moe, moet vaak rusten, bed niet uitkomen"
    ),
    "gewichtstoename": (
        "aangekomen, zwaarder geworden, weegschaal hoger, broek past niet, "
        "vocht vasthouden, snelle gewichtstoename"
    ),
    "borstpijn": (
        "pijn op de borst, druk op borst, stekende pijn borst, "
        "beklemming op de borst, pijn uitstralend naar arm"
    ),
    "duizeligheid": (
        "duizelig, draaierig, alles draait, bijna gevallen, "
        "zwart voor ogen, hoofd tolt, evenwicht kwijt"
    ),
}


def maak_embedding(tekst: str) -> list:
    """Zet een stuk tekst om naar een embedding vector via Ollama."""
    response = ollama.embeddings(model="nomic-embed-text", prompt=tekst)
    return response["embedding"]


def cosine_similarity(a: list, b: list) -> float:
    """Bereken hoe vergelijkbaar twee embeddings zijn (0 = niets, 1 = zelfde)."""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def vind_symptoom(tekst: str, drempel: float = 0.75) -> str | None:
    """
    Vergelijk wat de patient zei met bekende symptomen.
    Geeft de naam van het symptoom terug als de match goed genoeg is.
    """
    patient_embedding = maak_embedding(tekst)

    beste_match = None
    beste_score = 0.0

    for symptoom_naam, beschrijving in SYMPTOMEN.items():
        symptoom_embedding = maak_embedding(beschrijving)
        score = cosine_similarity(patient_embedding, symptoom_embedding)

        if score > beste_score:
            beste_score = score
            beste_match = symptoom_naam

    if beste_score >= drempel:
        return beste_match

    return None
