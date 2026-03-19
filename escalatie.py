import ollama

def analyseer_symptomen(gesprek):
    berichten_tekst = ""
    for bericht in gesprek:
        if bericht["role"] == "user":
            berichten_tekst += "Patient: " + bericht["content"] + "\n"

    analyse_vraag = """
Analyseer dit gesprek met een hartfalen patient en geef antwoord in dit exacte formaat:

kortademigheid: [getal 0-10 of onbekend]
enkelbewelling: [getal 0-10 of onbekend]
borstpijn: [ja of nee]
medicijnen_genomen: [ja, nee, of onbekend]
trend: [verslechterend, stabiel, of verbeterend]
escalatie_nodig: [ja of nee]
reden: [korte uitleg]

Gesprek:
""" + berichten_tekst

    antwoord = ollama.chat(
        model="gemma3:12b",
        messages=[{"role": "user", "content": analyse_vraag}]
    )

    return antwoord["message"]["content"]

def check_escalatie(analyze_tekst):
    tekst = analyze_tekst.lower()

    borstpijn_woorden = ["borstpijn: ja", "chest pain: yes", "borstpijn gemeld: ja", "heeft borstpijn"]
    for woord in borstpijn_woorden:
        if woord in tekst:
            return "NOODGEVAL", "Patient heeft borstpijn gemeld"
    
    escalatie_woorden = ["escalatie_nodig: ja", "escalatie nodig: ja", "escalation: yes", "direct contact"]
    for woord in escalatie_woorden:
        if woord in tekst:
            return "DRINGEND", "Analyse geeft aan dat escalatie nodig is"
    
    verslechter_woorden = ["trend: verslechterend", "verslechterd", "worsening"]
    for woord in verslechter_woorden:
        if woord in tekst:
            return "WAARSCHUWING", "Symptomen verslechteren"

    return None, None

def toon_escalatie_waarschuwing(patient, niveau, reden):
    print("\n" + "=" * 50)

    if niveau == "NOODGEVAL":
        print("!! NOODGEVAL - BEL DIRECT 112 !!")
    elif niveau == "DRINGEND":
        print("!! DRINGEND - NEEM CONTACT OP MET DOKTER !!")
    elif niveau == "WAARSCHUWING":
        print("!! WAARSCHUWING - HOUD PATIENT IN DE GATEN !!")

    print("Patient: " + patient["naam"])
    print("Reden: " + reden)
    print("=" * 50 + "\n")