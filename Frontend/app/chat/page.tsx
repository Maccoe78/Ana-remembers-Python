"use client";

import { useState, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";

const API = "http://localhost:8000";

type Bericht = {
  rol: "ana" | "gebruiker";
  tekst: string;
  tijd: string;
};

type EscalatieResultaat = {
  escalatie_niveau: string | null;
  reden: string | null;
};

function huidigetijd() {
  return new Date().toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" });
}

export default function ChatPagina() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const naam = searchParams.get("naam") || "";

  const [berichten, setBerichten] = useState<Bericht[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [laden, setLaden] = useState(false);
  const [gesprekKlaar, setGesprekKlaar] = useState(false);
  const [escalatie, setEscalatie] = useState<EscalatieResultaat | null>(null);
  const [opnemen, setOpnemen] = useState(false);
  const onderRef = useRef<HTMLDivElement>(null);
  const sessieGestart = useRef(false);
  const recorderRef = useRef<MediaRecorder | null>(null);

  const snelOpties = ["Kortademigheid", "Vermoeidheid", "Zwelling benen", "Slecht slapen"];

  // Sessie starten zodra pagina laadt
  useEffect(() => {
    if (!naam) {
      router.push("/");
      return;
    }
    if (sessieGestart.current) return;
    sessieGestart.current = true;
    startSessie();
  }, []);

  // Scroll naar beneden bij nieuw bericht
  useEffect(() => {
    onderRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [berichten]);

  async function speelAudio(tekst: string) {
    try {
      const res = await fetch(`${API}/text-to-speech`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bericht: tekst }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
    } catch {
      // stil falen als audio niet werkt
    }
  }

  async function startOpname() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("audio", blob, "opname.webm");

        try {
          const res = await fetch(`${API}/speech-to-text`, {
            method: "POST",
            body: formData,
          });
          const data = await res.json();
          await stuurBericht(data.tekst);
        } catch {
          setBerichten((prev) => [...prev, { rol: "ana", tekst: "Kon spraak niet verwerken.", tijd: huidigetijd() }]);
        }
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      recorderRef.current = recorder;
      setOpnemen(true);
    } catch {
      alert("Geen toegang tot microfoon.");
    }
  }

  function stopOpname() {
    recorderRef.current?.stop();
    setOpnemen(false);
  }

  async function startSessie() {
    setLaden(true);
    try {
      const res = await fetch(`${API}/patients/${encodeURIComponent(naam)}/session/start`, {
        method: "POST",
      });
      const data = await res.json();
      setSessionId(data.session_id);
      setBerichten([{ rol: "ana", tekst: data.ana_bericht, tijd: huidigetijd() }]);
      speelAudio(data.ana_bericht);
    } catch {
      setBerichten([{ rol: "ana", tekst: "Kon geen verbinding maken met de server.", tijd: huidigetijd() }]);
    }
    setLaden(false);
  }

  async function stuurBericht(tekst: string) {
    if (!tekst.trim() || !sessionId || gesprekKlaar) return;

    const gebruikerBericht: Bericht = { rol: "gebruiker", tekst, tijd: huidigetijd() };
    setBerichten((prev) => [...prev, gebruikerBericht]);
    setInput("");
    setLaden(true);

    try {
      const res = await fetch(
        `${API}/patients/${encodeURIComponent(naam)}/session/${sessionId}/message`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ bericht: tekst }),
        }
      );
      const data = await res.json();
      setBerichten((prev) => [...prev, { rol: "ana", tekst: data.ana_bericht, tijd: huidigetijd() }]);
      speelAudio(data.ana_bericht);

      if (data.gesprek_klaar) {
        setGesprekKlaar(true);
        await beeindigSessie();
      }
    } catch {
      setBerichten((prev) => [...prev, { rol: "ana", tekst: "Er ging iets mis.", tijd: huidigetijd() }]);
    }
    setLaden(false);
  }

  async function beeindigSessie() {
    if (!sessionId) return;
    try {
      const res = await fetch(
        `${API}/patients/${encodeURIComponent(naam)}/session/${sessionId}/end`,
        { method: "POST" }
      );
      const data = await res.json();
      setEscalatie(data);
    } catch {
      // stil falen
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-r from-red-500 to-red-600 text-white px-6 py-4 flex items-center justify-between shadow">
        <div className="flex items-center gap-3">
          <div className="bg-white rounded-xl w-10 h-10 flex items-center justify-center shadow">
            <span className="text-red-500 text-lg">♥</span>
          </div>
          <div>
            <h1 className="font-bold text-lg">Ana Remembers</h1>
            <p className="text-red-100 text-xs">Hartfalen monitoring</p>
          </div>
        </div>
        <div className="text-right text-sm">
          <p className="text-red-100">Patiënt</p>
          <p className="font-semibold">{naam}</p>
        </div>
      </div>

      {/* Berichten */}
      <div className="flex-1 overflow-y-auto px-4 py-6 flex flex-col gap-4 max-w-2xl w-full mx-auto">
        {berichten.map((b, i) => (
          <div key={i} className={`flex flex-col ${b.rol === "gebruiker" ? "items-end" : "items-start"}`}>
            <div className={`flex items-end gap-2 ${b.rol === "gebruiker" ? "flex-row-reverse" : ""}`}>
              {/* Avatar */}
              <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0 ${b.rol === "ana" ? "bg-red-500" : "bg-gray-400"}`}>
                {b.rol === "ana" ? "♥" : naam[0]?.toUpperCase()}
              </div>
              {/* Tekstballon */}
              <div className={`max-w-sm px-4 py-3 rounded-2xl text-sm leading-relaxed ${b.rol === "ana" ? "bg-white shadow text-gray-800" : "bg-red-500 text-white"}`}>
                {b.tekst}
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-1 mx-11">{b.tijd}</p>
          </div>
        ))}

        {/* Laad indicator */}
        {laden && (
          <div className="flex items-end gap-2">
            <div className="w-9 h-9 rounded-full bg-red-500 flex items-center justify-center text-white text-sm">♥</div>
            <div className="bg-white shadow px-4 py-3 rounded-2xl text-gray-400 text-sm">...</div>
          </div>
        )}

        {/* Escalatieresultaat */}
        {escalatie && (
          <div className={`rounded-2xl p-4 text-sm font-medium ${
            escalatie.escalatie_niveau === "NOODGEVAL" ? "bg-red-100 text-red-700 border border-red-300" :
            escalatie.escalatie_niveau === "DRINGEND" ? "bg-orange-100 text-orange-700 border border-orange-300" :
            escalatie.escalatie_niveau === "WAARSCHUWING" ? "bg-yellow-100 text-yellow-700 border border-yellow-300" :
            "bg-green-100 text-green-700 border border-green-300"
          }`}>
            {escalatie.escalatie_niveau === "NOODGEVAL" && "🚨 NOODGEVAL — Bel direct 112!"}
            {escalatie.escalatie_niveau === "DRINGEND" && "⚠️ Dringend — Neem contact op met uw dokter."}
            {escalatie.escalatie_niveau === "WAARSCHUWING" && "⚠️ Waarschuwing — Houd de symptomen in de gaten."}
            {!escalatie.escalatie_niveau && "✓ Alles lijkt stabiel. Tot de volgende check-in!"}
            {escalatie.reden && <p className="mt-1 font-normal">{escalatie.reden}</p>}
          </div>
        )}

        <div ref={onderRef} />
      </div>

      {/* Input */}
      {!gesprekKlaar && (
        <div className="max-w-2xl w-full mx-auto px-4 pb-6 pt-2 flex gap-2">
          <input
            type="text"
            placeholder="Typ je bericht..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && stuurBericht(input)}
            disabled={laden || opnemen}
            className="flex-1 border border-red-200 rounded-full px-5 py-3 text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-red-300 disabled:opacity-40"
          />
          <button
            onClick={opnemen ? stopOpname : startOpname}
            disabled={laden}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition disabled:opacity-40 ${opnemen ? "bg-red-700 animate-pulse" : "bg-gray-200 hover:bg-gray-300 text-gray-600"}`}
          >
            🎤
          </button>
          <button
            onClick={() => stuurBericht(input)}
            disabled={laden || input.trim() === "" || opnemen}
            className="w-12 h-12 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center transition disabled:opacity-40"
          >
            ➤
          </button>
        </div>
      )}

      {/* Terug knop na gesprek */}
      {gesprekKlaar && (
        <div className="max-w-2xl w-full mx-auto px-4 pb-6 pt-2">
          <button
            onClick={() => router.push("/")}
            className="w-full border border-red-300 text-red-500 rounded-xl py-3 text-sm hover:bg-red-50 transition"
          >
            Terug naar beginscherm
          </button>
        </div>
      )}
    </div>
  );
}
