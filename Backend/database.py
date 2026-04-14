import sqlite3
from datetime import datetime

DB_BESTAND = "ana.db"


def get_verbinding():
    """Geeft een verbinding met de database terug."""
    verbinding = sqlite3.connect(DB_BESTAND)
    verbinding.row_factory = sqlite3.Row  # zodat je kolommen bij naam kunt opvragen
    return verbinding


def initialiseer_database():
    """Maak de tabellen aan als ze nog niet bestaan."""
    with get_verbinding() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS patienten (
                naam TEXT PRIMARY KEY,
                medicijnen TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS sessies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_naam TEXT NOT NULL,
                datum TEXT NOT NULL,
                kortademigheid TEXT,
                enkelbezwelling TEXT,
                trend TEXT,
                escalatie_niveau TEXT,
                reden TEXT,
                samenvatting TEXT,
                FOREIGN KEY (patient_naam) REFERENCES patienten(naam)
            );

            CREATE TABLE IF NOT EXISTS berichten (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sessie_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (sessie_id) REFERENCES sessies(id)
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                naam TEXT PRIMARY KEY,
                beschrijving TEXT NOT NULL,
                vector TEXT NOT NULL
            );
        """)
        # Voeg samenvatting kolom toe als die nog niet bestaat (voor bestaande databases)
        try:
            db.execute("ALTER TABLE sessies ADD COLUMN samenvatting TEXT")
        except Exception:
            pass  # Kolom bestaat al


# ------------------------------------------------------------------
# Patienten
# ------------------------------------------------------------------

def patient_bestaat(naam: str) -> bool:
    with get_verbinding() as db:
        rij = db.execute(
            "SELECT naam FROM patienten WHERE naam = ?", (naam.lower().strip(),)
        ).fetchone()
        return rij is not None


def nieuwe_patient(naam: str):
    """Maak een nieuwe patient aan in de database en geef het dict terug."""
    veilige_naam = naam.lower().strip()
    with get_verbinding() as db:
        db.execute(
            "INSERT OR IGNORE INTO patienten (naam) VALUES (?)", (veilige_naam,)
        )
    return {"naam": veilige_naam, "medicijnen": []}


def laad_patient(naam: str) -> dict:
    """Laad een patient uit de database."""
    veilige_naam = naam.lower().strip()
    with get_verbinding() as db:
        rij = db.execute(
            "SELECT * FROM patienten WHERE naam = ?", (veilige_naam,)
        ).fetchone()
        if not rij:
            return None
        return {"naam": rij["naam"], "medicijnen": []}


# ------------------------------------------------------------------
# Sessies
# ------------------------------------------------------------------

def sla_sessie_op(patient_naam: str, geschiedenis: list, analyse: dict) -> int:
    """
    Sla een sessie op met de geanalyseerde symptoomdata.
    Geeft het sessie-id terug.
    """
    veilige_naam = patient_naam.lower().strip()
    datum = datetime.now().strftime("%Y-%m-%d %H:%M")

    with get_verbinding() as db:
        cursor = db.execute(
            """INSERT INTO sessies
               (patient_naam, datum, kortademigheid, enkelbezwelling, trend, escalatie_niveau, reden, samenvatting)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                veilige_naam,
                datum,
                analyse.get("kortademigheid"),
                analyse.get("enkelbezwelling"),
                analyse.get("trend"),
                analyse.get("escalatie_niveau"),
                analyse.get("reden"),
                analyse.get("samenvatting"),
            ),
        )
        sessie_id = cursor.lastrowid

        # Sla de ruwe berichten ook op
        for bericht in geschiedenis:
            db.execute(
                "INSERT INTO berichten (sessie_id, role, content) VALUES (?, ?, ?)",
                (sessie_id, bericht["role"], bericht["content"]),
            )

        return sessie_id


def maak_geheugen_samenvatting(patient_naam: str) -> str:
    """
    Bouw een compacte samenvatting van de laatste 3 sessies.
    Dit is wat naar het AI model wordt gestuurd als geheugen.
    """
    veilige_naam = patient_naam.lower().strip()

    with get_verbinding() as db:
        sessies = db.execute(
            """SELECT datum, kortademigheid, enkelbezwelling, trend, escalatie_niveau, samenvatting
               FROM sessies
               WHERE patient_naam = ?
               ORDER BY datum DESC
               LIMIT 3""",
            (veilige_naam,),
        ).fetchall()

    if not sessies:
        return "Dit is de eerste keer met deze patient."

    samenvatting = "Vorige sessies met deze patient:\n"
    for s in reversed(sessies):  # oudste eerst
        samenvatting += f"\nSessie op {s['datum']}:\n"
        if s["samenvatting"]:
            samenvatting += f"  - Wat de patient zei: {s['samenvatting']}\n"
        if s["kortademigheid"]:
            samenvatting += f"  - Kortademigheid: {s['kortademigheid']}/10\n"
        if s["enkelbezwelling"]:
            samenvatting += f"  - Enkelbezwelling: {s['enkelbezwelling']}/10\n"
        if s["trend"]:
            samenvatting += f"  - Trend: {s['trend']}\n"
        if s["escalatie_niveau"]:
            samenvatting += f"  - Escalatie: {s['escalatie_niveau']}\n"

    return samenvatting


def haal_sessies_op(patient_naam: str) -> list:
    """Haal alle sessies op van een patient voor het dashboard."""
    veilige_naam = patient_naam.lower().strip()
    with get_verbinding() as db:
        sessies = db.execute(
            """SELECT id, datum, kortademigheid, enkelbezwelling, trend, escalatie_niveau
               FROM sessies WHERE patient_naam = ? ORDER BY datum DESC""",
            (veilige_naam,),
        ).fetchall()
        return [dict(s) for s in sessies]


# Initialiseer de database bij het importeren van dit bestand
initialiseer_database()


# ------------------------------------------------------------------
# Embeddings
# ------------------------------------------------------------------

def sla_embedding_op(naam: str, beschrijving: str, vector: list):
    """Sla een symptoom-embedding op in de database."""
    import json
    with get_verbinding() as db:
        db.execute(
            "INSERT OR REPLACE INTO embeddings (naam, beschrijving, vector) VALUES (?, ?, ?)",
            (naam, beschrijving, json.dumps(vector)),
        )


def laad_embedding(naam: str) -> list | None:
    """Haal een opgeslagen embedding op. Geeft None terug als die niet bestaat."""
    import json
    with get_verbinding() as db:
        rij = db.execute(
            "SELECT vector FROM embeddings WHERE naam = ?", (naam,)
        ).fetchone()
        if rij:
            return json.loads(rij["vector"])
        return None


def laad_alle_embeddings() -> dict:
    """Laad alle opgeslagen embeddings als dict {naam: vector}."""
    import json
    with get_verbinding() as db:
        rijen = db.execute("SELECT naam, vector FROM embeddings").fetchall()
        return {r["naam"]: json.loads(r["vector"]) for r in rijen}
