import ollama
from patient_manager import *
from escalatie import *

naam = input("Wat is jou naam? ")
if patient_bestaat(naam):
    patient = laad_patient(naam)
    print("welkom terug " + naam)
else:
    patient = nieuwe_patient(naam)
    print("Hallo " + naam )

geheugen = maak_geheugen_samenvatting(patient)

geschiedenis = [
    {
        "role": "system",
        "content": "Jij bent Ana, een vriendelijke zorgassistent voor hartfalen patienten. "
                   "De patient heet " + naam + ". "
                   "Stel vragen over: kortademigheid, enkelbewelling, gewicht, en medicijnen. "
                   "Stel elke keer maar een vraag. "
                   "Verwijs naar eerdere gesprekken als dat relevant is. "
                   "\n\n" + geheugen
    }
]

eerste_bericht = ollama.chat(
    model="gemma3:12b",
    messages=geschiedenis + [{"role": "user", "content": "Start de check-in"}]
)

eerste_tekst = eerste_bericht["message"]["content"]
print("Ana:", eerste_tekst)
geschiedenis.append({"role": "assistant", "content": eerste_tekst})

while True:
    gebruiker_input = input("Jij: ")

    if gebruiker_input.lower() == "stop":
        print("Gesprek beëindigd.")
        break

    geschiedenis.append({"role": "user", "content": gebruiker_input})

    antwoord = ollama.chat(
        model="gemma3:12b",
        messages=geschiedenis
    )

    ana_tekst = antwoord["message"]["content"]
    print("Ana:", ana_tekst)
    geschiedenis.append({"role": "assistant", "content": ana_tekst})

voeg_sessie_toe(patient, geschiedenis)

print("\nAna analyseert het gesprek...")
analyse = analyseer_symptomen(geschiedenis)
niveau, reden = check_escalatie(analyse)

if niveau:
    toon_escalatie_waarschuwing(patient, niveau, reden)
else:
    print("Geen escalatie nodig. Alles lijkt stabiel.")
    
sla_patient_op(patient)
print("sessie opgeslagen.")
