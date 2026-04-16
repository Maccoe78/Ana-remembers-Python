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

function DoctorAvatar({ spreekt, laden }: { spreekt: boolean; laden: boolean }) {
  return (
    <svg viewBox="0 0 200 220" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      {/* Achtergrond */}
      <circle cx="100" cy="100" r="100" fill="url(#bgGrad)" />

      {/* Haar */}
      <ellipse cx="100" cy="62" rx="38" ry="42" fill="#3b1f0a" />
      <ellipse cx="100" cy="58" rx="30" ry="34" fill="#4a2810" />
      <ellipse cx="68" cy="80" rx="14" ry="22" fill="#3b1f0a" />
      <ellipse cx="132" cy="80" rx="14" ry="22" fill="#3b1f0a" />

      {/* Gezicht */}
      <ellipse cx="100" cy="88" rx="30" ry="34" fill="#f5c5a3" />

      {/* Ogen */}
      <ellipse cx="88" cy="82" rx="5" ry="5.5" fill="white" />
      <ellipse cx="112" cy="82" rx="5" ry="5.5" fill="white" />
      <circle cx="89" cy="83" r="3" fill="#3b2b1a" />
      <circle cx="113" cy="83" r="3" fill="#3b2b1a" />
      <circle cx="90" cy="82" r="1" fill="white" />
      <circle cx="114" cy="82" r="1" fill="white" />

      {/* Wenkbrauwen */}
      <path d="M83 76 Q88 73 93 76" stroke="#3b1f0a" strokeWidth="2" strokeLinecap="round" />
      <path d="M107 76 Q112 73 117 76" stroke="#3b1f0a" strokeWidth="2" strokeLinecap="round" />

      {/* Neus */}
      <path d="M100 87 Q97 94 100 96 Q103 94 100 87" fill="#e8a882" />

      {/* Mond - beweegt als ze spreekt */}
      {spreekt ? (
        <ellipse cx="100" cy="103" rx="8" ry="5" fill="#c0624a" />
      ) : (
        <path d="M92 102 Q100 108 108 102" stroke="#c0624a" strokeWidth="2.5" strokeLinecap="round" fill="none" />
      )}

      {/* Oren */}
      <ellipse cx="70" cy="88" rx="5" ry="7" fill="#f5c5a3" />
      <ellipse cx="130" cy="88" rx="5" ry="7" fill="#f5c5a3" />

      {/* Nek */}
      <rect x="91" y="118" width="18" height="16" fill="#f5c5a3" />

      {/* Witte jas */}
      <path d="M55 180 L60 130 Q70 122 91 120 L100 140 L109 120 Q130 122 140 130 L145 180 Z" fill="white" />

      {/* Blouse onder jas */}
      <path d="M80 130 Q100 125 120 130 L118 180 L82 180 Z" fill="#e8f4f8" />

      {/* Jas revers */}
      <path d="M91 120 L85 145 L75 145 L60 130 Q70 122 91 120Z" fill="#f0f0f0" />
      <path d="M109 120 L115 145 L125 145 L140 130 Q130 122 109 120Z" fill="#f0f0f0" />

      {/* Stethoscoop */}
      <path d="M85 130 Q78 138 78 148 Q78 158 86 160 Q94 162 96 155" stroke="#c0392b" strokeWidth="3" fill="none" strokeLinecap="round" />
      <circle cx="96" cy="152" r="5" fill="#c0392b" />
      <path d="M115 130 Q122 138 122 148 Q122 158 114 160 Q106 162 104 155" stroke="#c0392b" strokeWidth="3" fill="none" strokeLinecap="round" />

      {/* Laden animatie - ring */}
      {laden && (
        <circle cx="100" cy="100" r="95" stroke="white" strokeWidth="4" strokeDasharray="60 540" strokeLinecap="round" opacity="0.8">
          <animateTransform attributeName="transform" type="rotate" from="0 100 100" to="360 100 100" dur="1s" repeatCount="indefinite" />
        </circle>
      )}

      <defs>
        <radialGradient id="bgGrad" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#1a4a6b" />
          <stop offset="100%" stopColor="#0d2b3e" />
        </radialGradient>
      </defs>
    </svg>
  );
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
  const [anaSpreekt, setAnaSpreekt] = useState(false);
  const [huidigBericht, setHuidigBericht] = useState("");
  const [chatOpen, setChatOpen] = useState(false);
  const sessieGestart = useRef(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const onderRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!naam) { router.push("/"); return; }
    if (sessieGestart.current) return;
    sessieGestart.current = true;
    startSessie();
  }, []);

  useEffect(() => {
    onderRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [berichten]);

  async function speelAudio(tekst: string, onEinde?: () => void) {
    setAnaSpreekt(true);
    try {
      const res = await fetch(`${API}/text-to-speech`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bericht: tekst }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => { setAnaSpreekt(false); onEinde?.(); };
      audio.play();
    } catch {
      setAnaSpreekt(false);
      onEinde?.();
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
          const res = await fetch(`${API}/speech-to-text`, { method: "POST", body: formData });
          const data = await res.json();
          await stuurBericht(data.tekst);
        } catch {
          setHuidigBericht("Kon spraak niet verwerken.");
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
      const res = await fetch(`${API}/patients/${encodeURIComponent(naam)}/session/start`, { method: "POST" });
      const data = await res.json();
      setSessionId(data.session_id);
      setBerichten([{ rol: "ana", tekst: data.ana_bericht, tijd: huidigetijd() }]);
      setHuidigBericht(data.ana_bericht);
      speelAudio(data.ana_bericht);
    } catch {
      setHuidigBericht("Kon geen verbinding maken met de server.");
    }
    setLaden(false);
  }

  async function stuurBericht(tekst: string) {
    if (!tekst.trim() || !sessionId || gesprekKlaar) return;

    setBerichten((prev) => [...prev, { rol: "gebruiker", tekst, tijd: huidigetijd() }]);
    setInput("");
    setLaden(true);

    try {
      const res = await fetch(
        `${API}/patients/${encodeURIComponent(naam)}/session/${sessionId}/message`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ bericht: tekst }) }
      );
      const data = await res.json();
      const anaBericht = data.ana_bericht;
      setBerichten((prev) => [...prev, { rol: "ana", tekst: anaBericht, tijd: huidigetijd() }]);

      if (data.gesprek_klaar) {
        setGesprekKlaar(true);
        setHuidigBericht(anaBericht);
        await beeindigSessie();
        speelAudio(anaBericht, () => setTimeout(() => router.push("/"), 3000));
      } else {
        setHuidigBericht(anaBericht);
        speelAudio(anaBericht);
      }
    } catch {
      setHuidigBericht("Er ging iets mis.");
    }
    setLaden(false);
  }

  async function beeindigSessie() {
    if (!sessionId) return;
    try {
      const res = await fetch(`${API}/patients/${encodeURIComponent(naam)}/session/${sessionId}/end`, { method: "POST" });
      const data = await res.json();
      setEscalatie(data);
    } catch { /* stil falen */ }
  }

  const statusLabel = gesprekKlaar && !anaSpreekt ? "Gesprek afgerond, verbinding verbreken..." : opnemen ? "Luistert naar jou..." : laden ? "Aan het denken..." : anaSpreekt ? "Ana is aan het spreken..." : "Klaar voor antwoord";
  const statusKleur = gesprekKlaar && !anaSpreekt ? "text-slate-500" : opnemen ? "text-red-400" : laden ? "text-yellow-400" : anaSpreekt ? "text-green-400" : "text-slate-400";

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col relative overflow-hidden">

      {/* Achtergrond glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-900 opacity-20 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between px-6 py-3 bg-slate-900/80 backdrop-blur border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-red-400 text-lg">♥</span>
          <span className="text-white font-semibold text-sm">Ana Remembers</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-green-400 text-xs font-medium">Live</span>
        </div>
        <div className="text-right">
          <p className="text-slate-400 text-xs">Patiënt</p>
          <p className="text-white text-sm font-semibold">{naam}</p>
        </div>
      </div>

      {/* Video call area */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 py-6 gap-4">

        {/* Ana's video frame */}
        <div className="relative">
          {/* Spreek-ring animatie */}
          {anaSpreekt && (
            <div className="absolute inset-0 rounded-full ring-4 ring-green-400 animate-ping opacity-30 scale-110" />
          )}
          <div className={`relative w-56 h-56 rounded-full overflow-hidden shadow-2xl transition-all duration-300 ${anaSpreekt ? "ring-4 ring-green-400 shadow-green-900" : "ring-2 ring-slate-700"}`}>
            <DoctorAvatar spreekt={anaSpreekt} laden={laden} />
          </div>
        </div>

        {/* Naam & status */}
        <div className="text-center">
          <p className="text-white font-semibold text-lg">Ana</p>
          <p className="text-slate-400 text-xs">Hartfalen Verpleegkundige</p>
          <p className={`text-xs mt-1 font-medium ${statusKleur}`}>{statusLabel}</p>
        </div>

        {/* Ondertitels / huidig bericht */}
        {huidigBericht && !huidigBericht.startsWith("Gesprek_") && (
          <div className="max-w-sm w-full bg-black/60 backdrop-blur rounded-2xl px-5 py-3 text-center">
            <p className="text-white text-sm leading-relaxed">{huidigBericht}</p>
          </div>
        )}

        {/* Escalatie resultaat */}
        {escalatie && (
          <div className={`max-w-sm w-full rounded-2xl px-5 py-4 text-sm font-medium text-center ${
            escalatie.escalatie_niveau === "NOODGEVAL" ? "bg-red-900/80 text-red-200 border border-red-600" :
            escalatie.escalatie_niveau === "DRINGEND" ? "bg-orange-900/80 text-orange-200 border border-orange-600" :
            escalatie.escalatie_niveau === "WAARSCHUWING" ? "bg-yellow-900/80 text-yellow-200 border border-yellow-600" :
            "bg-green-900/80 text-green-200 border border-green-600"
          }`}>
            {escalatie.escalatie_niveau === "NOODGEVAL" && "🚨 NOODGEVAL — Bel direct 112!"}
            {escalatie.escalatie_niveau === "DRINGEND" && "⚠️ Dringend — Neem contact op met uw dokter."}
            {escalatie.escalatie_niveau === "WAARSCHUWING" && "⚠️ Waarschuwing — Houd de symptomen in de gaten."}
            {!escalatie.escalatie_niveau && "✓ Alles lijkt stabiel. Tot de volgende check-in!"}
            {escalatie.reden && <p className="mt-1 font-normal opacity-80">{escalatie.reden}</p>}
          </div>
        )}

        {/* Patiënt klein scherm (rechtsonder) */}
        <div className="absolute bottom-24 right-4 w-20 h-20 rounded-2xl bg-slate-800 border border-slate-700 shadow-lg flex flex-col items-center justify-center overflow-hidden">
          <div className="w-10 h-10 rounded-full bg-red-500 flex items-center justify-center text-white font-bold text-lg">
            {naam[0]?.toUpperCase()}
          </div>
          <p className="text-slate-400 text-xs mt-1 truncate max-w-full px-1 text-center">{naam.split(" ")[0]}</p>
        </div>
      </div>

      {/* Onderste bediening */}
      {!gesprekKlaar ? (
        <div className="relative z-10 pb-8 pt-2 flex flex-col items-center gap-4 bg-gradient-to-t from-slate-950 to-transparent">

          {/* Tekst invoer */}
          <div className="flex items-center gap-2 max-w-sm w-full px-4">
            <input
              type="text"
              placeholder="Of typ hier..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && stuurBericht(input)}
              disabled={laden || opnemen}
              className="flex-1 bg-slate-800 border border-slate-700 text-white rounded-full px-4 py-2 text-sm placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:opacity-40"
            />
            <button
              onClick={() => stuurBericht(input)}
              disabled={laden || input.trim() === "" || opnemen}
              className="w-10 h-10 bg-blue-600 hover:bg-blue-500 text-white rounded-full flex items-center justify-center transition disabled:opacity-40"
            >
              ➤
            </button>
          </div>

          {/* Mic & ophangen knoppen */}
          <div className="flex items-center gap-6">
            {/* Chat toggle */}
            <button
              onClick={() => setChatOpen(!chatOpen)}
              className="w-12 h-12 rounded-full bg-slate-700 hover:bg-slate-600 text-white flex items-center justify-center transition text-lg"
            >
              💬
            </button>

            {/* Microfoon — grote knop */}
            <button
              onMouseDown={startOpname}
              onMouseUp={stopOpname}
              onTouchStart={startOpname}
              onTouchEnd={stopOpname}
              disabled={laden}
              className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl shadow-lg transition-all disabled:opacity-40 ${
                opnemen ? "bg-red-600 animate-pulse scale-110 ring-4 ring-red-400" : "bg-slate-700 hover:bg-slate-600"
              }`}
            >
              🎤
            </button>

            {/* Ophangen */}
            <button
              onClick={() => router.push("/")}
              className="w-12 h-12 rounded-full bg-red-600 hover:bg-red-500 text-white flex items-center justify-center transition text-xl"
            >
              📵
            </button>
          </div>

          <p className="text-slate-600 text-xs">Houd de microfoon ingedrukt om te spreken</p>
        </div>
      ) : (
        <div className="relative z-10 pb-8 flex flex-col items-center gap-3 px-4">
          <button
            onClick={() => router.push("/")}
            className="w-full max-w-sm border border-slate-600 text-slate-300 rounded-xl py-3 text-sm hover:bg-slate-800 transition"
          >
            Terug naar beginscherm
          </button>
        </div>
      )}

      {/* Chat geschiedenis overlay */}
      {chatOpen && (
        <div className="absolute inset-0 z-20 bg-slate-950/95 flex flex-col">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
            <h2 className="text-white font-semibold">Gesprek</h2>
            <button onClick={() => setChatOpen(false)} className="text-slate-400 hover:text-white text-xl">✕</button>
          </div>
          <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
            {berichten.map((b, i) => (
              <div key={i} className={`flex flex-col ${b.rol === "gebruiker" ? "items-end" : "items-start"}`}>
                <div className={`max-w-xs px-4 py-2 rounded-2xl text-sm ${b.rol === "ana" ? "bg-slate-800 text-white" : "bg-blue-600 text-white"}`}>
                  {b.tekst}
                </div>
                <p className="text-xs text-slate-600 mt-1">{b.tijd}</p>
              </div>
            ))}
            <div ref={onderRef} />
          </div>
        </div>
      )}
    </div>
  );
}
