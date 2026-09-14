import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Mic, Square, Camera, CheckCircle2, Loader2, Languages, ShieldCheck,
  AlertTriangle, PartyPopper,
} from "lucide-react";

const pub = axios.create({ baseURL: API });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function withRetry(fn, attempts = 3) {
  let last;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (e) {
      last = e;
      if (i < attempts - 1) await sleep(800 * (i + 1));
    }
  }
  throw last;
}

function QuestionCard({ sessionId, q, answer, onAnswered }) {
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const recRef = useRef(null);

  const send = async (blob) => {
    setBusy(true);
    setErr("");
    const fd = new FormData();
    const ext = (blob.type && blob.type.includes("mp4")) ? "m4a" : "webm";
    fd.append("file", blob, `reponse.${ext}`);
    try {
      const { data } = await withRetry(() =>
        pub.post(`/amorce/${sessionId}/audio?question_key=${q.key}`, fd));
      onAnswered(q.key, data);
      if (data.warning) setErr(data.warning);
    } catch (e) {
      setErr("Échec de l'envoi. Vérifiez votre connexion et réessayez.");
    } finally {
      setBusy(false);
    }
  };

  const start = async () => {
    setErr("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      const chunks = [];
      mr.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        await send(new Blob(chunks, { type: mr.mimeType || "audio/webm" }));
      };
      recRef.current = mr;
      mr.start();
      setRecording(true);
    } catch (e) {
      setErr("Micro inaccessible. Autorisez le microphone dans votre navigateur.");
    }
  };

  const stop = () => recRef.current && recRef.current.stop();

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm" data-testid={`amorce-q-${q.key}`}>
      <div className="flex items-start gap-2">
        <span className={`mt-0.5 shrink-0 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold ${answer ? "bg-emerald-100 text-emerald-700" : "bg-[#0F2B48]/10 text-[#0F2B48]"}`}>
          {answer ? <CheckCircle2 size={16} /> : q.key.replace("q", "").split("_")[0]}
        </span>
        <div className="flex-1">
          <p className="text-sm font-semibold text-[#0F2B48] leading-snug">{q.question}</p>
          {q.optional && <span className="text-[11px] text-slate-400">Facultatif</span>}
          {q.aide && <p className="mt-1 text-[12px] text-slate-500">{q.aide}</p>}
        </div>
      </div>

      <div className="mt-3">
        {!recording ? (
          <Button
            onClick={start}
            disabled={busy}
            className="w-full bg-[#0F2B48] hover:bg-[#0F2B48]/90"
            data-testid={`amorce-record-${q.key}`}
          >
            {busy ? <Loader2 size={16} className="mr-2 animate-spin" /> : <Mic size={16} className="mr-2" />}
            {busy ? "Traitement…" : answer ? "Réenregistrer la réponse" : "Enregistrer ma réponse"}
          </Button>
        ) : (
          <Button
            onClick={stop}
            className="w-full bg-red-600 hover:bg-red-700 animate-pulse"
            data-testid={`amorce-stop-${q.key}`}
          >
            <Square size={16} className="mr-2" /> Arrêter l'enregistrement
          </Button>
        )}
      </div>

      {answer && (
        <div className="mt-3 rounded-xl bg-emerald-50 border border-emerald-200 p-3" data-testid={`amorce-answer-${q.key}`}>
          <div className="flex items-center gap-1 text-[11px] text-emerald-700 font-semibold uppercase tracking-wide">
            <Languages size={12} /> Réponse (français){answer.lang ? ` · langue détectée : ${answer.lang}` : ""}
          </div>
          <p className="mt-1 text-sm text-slate-800">{answer.transcript_fr || "—"}</p>
          {answer.transcript_original && answer.transcript_fr !== answer.transcript_original && (
            <p className="mt-1 text-[12px] text-slate-500 italic">Transcription : « {answer.transcript_original} »</p>
          )}
        </div>
      )}

      {err && <p className="mt-2 text-[12px] text-amber-700 flex items-center gap-1"><AlertTriangle size={12} /> {err}</p>}
    </div>
  );
}

function PhotoCard({ sessionId, cat, count, noJob, onUploaded, onNoJob }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const inputRef = useRef(null);

  const pick = () => inputRef.current && inputRef.current.click();

  const onFile = async (e) => {
    const f = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!f) return;
    setBusy(true);
    setErr("");
    const fd = new FormData();
    fd.append("file", f, f.name || "photo.jpg");
    try {
      await withRetry(() => pub.post(`/amorce/${sessionId}/photo?category=${cat.key}`, fd));
      onUploaded(cat.key);
    } catch (e2) {
      setErr("Échec de l'envoi. Réessayez.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm" data-testid={`amorce-photo-${cat.key}`}>
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-[#0F2B48]">{cat.label}</p>
          <p className="text-[12px] text-slate-500">{cat.hint}</p>
        </div>
        {count > 0 && (
          <span className="shrink-0 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold px-2 py-1" data-testid={`amorce-photo-count-${cat.key}`}>
            {count} ✓
          </span>
        )}
      </div>
      <input ref={inputRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={onFile} data-testid={`amorce-photo-input-${cat.key}`} />
      <Button variant="outline" onClick={pick} disabled={busy} className="mt-3 w-full border-[#0F2B48]/30 text-[#0F2B48]" data-testid={`amorce-photo-btn-${cat.key}`}>
        {busy ? <Loader2 size={16} className="mr-2 animate-spin" /> : <Camera size={16} className="mr-2" />}
        {busy ? "Envoi…" : count > 0 ? "Ajouter une autre photo" : "Prendre / choisir une photo"}
      </Button>

      {cat.key === "offre_emploi" && (
        <label className="mt-2 flex items-center gap-2 text-[12px] text-slate-600" data-testid="amorce-no-job">
          <input type="checkbox" checked={!!noJob} onChange={(e) => onNoJob(e.target.checked)} />
          Aucune offre d'emploi actuellement affichée
        </label>
      )}
      {err && <p className="mt-2 text-[12px] text-amber-700 flex items-center gap-1"><AlertTriangle size={12} /> {err}</p>}
    </div>
  );
}

export default function MobileAmorce() {
  const { sessionId } = useParams();
  const [info, setInfo] = useState(null);
  const [answers, setAnswers] = useState({});
  const [photoCounts, setPhotoCounts] = useState({});
  const [noJob, setNoJob] = useState(false);
  const [loadErr, setLoadErr] = useState("");
  const [done, setDone] = useState(false);
  const [finishing, setFinishing] = useState(false);

  useEffect(() => {
    pub.get(`/amorce/${sessionId}`)
      .then(({ data }) => {
        setInfo(data);
        setAnswers(data.answers || {});
        const pc = {};
        (data.photos || []).forEach((p) => { pc[p.category] = (pc[p.category] || 0) + 1; });
        setPhotoCounts(pc);
        setNoJob(!!(data.declarations && data.declarations.no_job_posting));
        if (data.status === "completed") setDone(true);
      })
      .catch((e) => setLoadErr(e.response?.data?.detail || "Lien invalide ou expiré."));
  }, [sessionId]);

  const onAnswered = (key, data) => setAnswers((a) => ({ ...a, [key]: { ...data, transcript_fr: data.transcript_fr } }));
  const onUploaded = (key) => setPhotoCounts((c) => ({ ...c, [key]: (c[key] || 0) + 1 }));
  const onNoJob = async (v) => {
    setNoJob(v);
    try { await pub.post(`/amorce/${sessionId}/declaration`, { no_job_posting: v }); } catch (_) {}
  };

  const finish = async () => {
    setFinishing(true);
    try {
      await pub.post(`/amorce/${sessionId}/complete`);
      setDone(true);
    } catch (e) {
      setLoadErr(e.response?.data?.detail || "Impossible de terminer.");
    } finally {
      setFinishing(false);
    }
  };

  if (loadErr && !info) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="max-w-sm text-center" data-testid="amorce-error">
          <AlertTriangle className="mx-auto text-amber-500 mb-3" size={40} />
          <p className="text-slate-700 font-medium">{loadErr}</p>
        </div>
      </div>
    );
  }
  if (!info) {
    return <div className="min-h-screen flex items-center justify-center text-slate-400">Chargement…</div>;
  }
  if (done || info.status !== "active") {
    const msg = done ? "Merci ! L'amorce est complétée." :
      info.status === "expired" ? "Ce lien a expiré. Demandez un nouveau code QR." :
      info.status === "revoked" ? "Ce lien a été révoqué." :
      "Cette amorce est déjà complétée.";
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="max-w-sm text-center" data-testid="amorce-done">
          <PartyPopper className="mx-auto text-emerald-500 mb-3" size={44} />
          <p className="text-lg font-bold text-[#0F2B48]">{msg}</p>
          <p className="mt-2 text-sm text-slate-500">Vous pouvez fermer cette page et revenir à l'ordinateur.</p>
        </div>
      </div>
    );
  }

  const answeredCount = Object.keys(answers).length;

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="bg-[#0F2B48] text-white px-4 py-5">
        <div className="flex items-center gap-2 text-sm opacity-80"><ShieldCheck size={16} /> CONFORMISTE — Amorce mobile</div>
        <h1 className="mt-1 font-bold text-lg leading-tight">{info.dossier_nom || "Votre entreprise"}</h1>
        <p className="text-[13px] opacity-80 mt-1">Répondez de vive voix (dans votre langue) et prenez quelques photos. Tout est envoyé directement au dossier.</p>
      </div>

      <div className="max-w-md mx-auto px-4 py-5 space-y-5">
        <section>
          <h2 className="text-sm font-bold text-slate-700 mb-2">Questions ({answeredCount}/{info.questions.length})</h2>
          <div className="space-y-3">
            {info.questions.map((q) => (
              <QuestionCard key={q.key} sessionId={sessionId} q={q} answer={answers[q.key]} onAnswered={onAnswered} />
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-sm font-bold text-slate-700 mb-2">Photos</h2>
          <div className="space-y-3">
            {info.photo_categories.map((cat) => (
              <PhotoCard key={cat.key} sessionId={sessionId} cat={cat}
                count={photoCounts[cat.key] || 0} noJob={noJob}
                onUploaded={onUploaded} onNoJob={onNoJob} />
            ))}
          </div>
        </section>

        <Button onClick={finish} disabled={finishing} className="w-full h-12 bg-emerald-600 hover:bg-emerald-700 text-base" data-testid="amorce-finish">
          {finishing ? <Loader2 size={18} className="mr-2 animate-spin" /> : <CheckCircle2 size={18} className="mr-2" />}
          Terminer l'amorce
        </Button>
        <p className="text-center text-[11px] text-slate-400 pb-6">Le lien se désactive dès que vous terminez.</p>
      </div>
    </div>
  );
}
