import json
import os
from datetime import datetime

MAP_NAAM = "patient_data"

def voeg_sessie_toe(patient, gesprek):
    sessie = {
        "datum": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "berichten": gesprek
    }
    patient["sessies"].append(sessie)

def maak_map_aan():
    if not os.path.exists(MAP_NAAM):
        os.makedirs(MAP_NAAM)

def patient_bestand(naam):
    veilige_naam = naam.lower().strip().replace(" ", "_")
    return os.path.join(MAP_NAAM, veilige_naam + ".json")

def patient_bestaat(naam):
    return os.path.exists(patient_bestand(naam))

def nieuwe_patient(naam):
    return {
        "naam": naam,  
        "medicijnen": [],
        "sessies": []
    }

def laad_patient(naam):
    with open(patient_bestand(naam), "r") as bestand:
        return json.load(bestand)

def sla_patient_op(patient):
    maak_map_aan()
    with open(patient_bestand(patient["naam"]), "w") as bestand:
        json.dump(patient, bestand, indent=2)

def maak_geheugen_samenvatting(patient):
    sessies = patient["sessies"]

    if len(sessies) == 0:
        return "Dit is de eerste keer met deze patient."
    
    samenvatting = "Vorige sessies met deze patient:\n"

    for sessie in sessies[-3:]:
        samenvatting += "\nSessie op " + sessie["datum"] + ":\n"
        for bericht in sessie["berichten"]:
            if bericht["role"] == "user":
                samenvatting += " Patient zei: " + bericht["content"] + "\n"

    return samenvatting