import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  QrCode, Smartphone, RefreshCw, XCircle, CheckCircle2, Camera, Mic, Languages, Clock,
} from "lucide-react";

function fmtCountdown(iso) {
  if (!iso) return "";
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "expiré";
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m} min ${String(s).padStart(2, "0")} s`;
}

export const AmorcePanel = ({ dossier }) => {
  const [session, setSession] = useState(null);
  const [busy, setBusy] = useState(false);
  const [, setTick] = useState(0);
  const pollRef = useRef(null);

  const mobileUrl = session?.session_id
    ? `${window.location.origin}/m/${session.session_id}`
    : "";

  const load = async () => {
    try {
      const { data } = await api.get(`/dossiers/${dossier.id}/amorce/session`);
      setSession(data.status === "none" ? null : data);
    } catch (_) {}
  };

  useEffect(() => { load(); }, [dossier.id]);

  // Polling en temps réel tant qu'une session est active, + horloge du compte à rebours.
  useEffect(() => {
    clearInterval(pollRef.current);
    if (session && session.status === "active") {
      pollRef.current = setInterval(() => { load(); setTick((t) => t + 1); }, 4000);
    }
    const clock = setInterval(() => setTick((t) => t + 1), 1000);
    return () => { clearInterval(pollRef.current); clearInterval(clock); };
  }, [session?.status, session?.session_id]);

  const generate = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/dossiers/${dossier.id}/amorce/session`);
      setSession(data);
      toast.success("Lien QR généré");
    } catch (e) { toast.error("Erreur lors de la génération"); }
    finally { setBusy(false); }
  };

  const revoke = async () => {
    setBusy(true);
    try {
      await api.post(`/dossiers/${dossier.id}/amorce/session/revoke`);
      await load();
      toast.success("Lien révoqué");
    } catch (e) { toast.error("Erreur"); }
    finally { setBusy(false); }
  };

  const isActive = session && session.status === "active";
  const answers = (session && session.answers) || {};
  const questions = (session && session.questions) || [];
  const photos = (session && session.photos) || [];
  const cats = (session && session.photo_categories) || [];
  const photoCounts = {};
  photos.forEach((p) => { photoCounts[p.category] = (photoCounts[p.category] || 0) + 1; });

  return (
    <Card className="p-6 space-y-5" data-testid="amorce-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-lg font-bold text-[#0F2B48] flex items-center gap-2">
            <Smartphone size={18} /> Amorce mobile
          </h3>
          <p className="text-sm text-slate-500 max-w-xl">
            Démarrez le dossier depuis le terrain : scannez le code QR avec un téléphone pour capturer des photos
            (façade, enseigne, affichage…) et répondre de vive voix à 5 questions. Les réponses sont transcrites
            et traduites en français automatiquement.
          </p>
        </div>
        {!isActive && (
          <Button onClick={generate} disabled={busy} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid="amorce-generate">
            <QrCode size={16} className="mr-2" /> Générer un lien QR
          </Button>
        )}
      </div>

      {isActive && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="flex flex-col items-center text-center rounded-2xl border border-slate-200 bg-slate-50 p-5" data-testid="amorce-qr">
            <div className="bg-white p-3 rounded-xl shadow-sm">
              <QRCodeSVG value={mobileUrl} size={180} level="M" />
            </div>
            <p className="mt-3 text-sm font-medium text-slate-700 flex items-center gap-1">
              <Clock size={14} /> Expire dans {fmtCountdown(session.expires_at)}
            </p>
            <a href={mobileUrl} target="_blank" rel="noreferrer" className="mt-2 text-xs text-[#0F2B48] underline break-all" data-testid="amorce-mobile-link">
              {mobileUrl}
            </a>
            <Button variant="outline" size="sm" onClick={revoke} disabled={busy} className="mt-3 text-red-600 border-red-200 hover:bg-red-50" data-testid="amorce-revoke">
              <XCircle size={14} className="mr-1" /> Révoquer le lien
            </Button>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex items-center gap-1 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                <Mic size={13} /> Réponses vocales ({Object.keys(answers).length}/{questions.length})
              </div>
              <div className="space-y-2">
                {questions.map((q) => {
                  const a = answers[q.key];
                  return (
                    <div key={q.key} className={`rounded-lg px-3 py-2 text-sm border ${a ? "bg-emerald-50 border-emerald-200" : "bg-slate-50 border-slate-200"}`} data-testid={`amorce-answer-row-${q.key}`}>
                      <div className="flex items-center gap-1 text-[12px] text-slate-500">
                        {a ? <CheckCircle2 size={13} className="text-emerald-600" /> : <span className="w-3 h-3 rounded-full border border-slate-300 inline-block" />}
                        <span className="line-clamp-1">{q.question}</span>
                      </div>
                      {a && (
                        <p className="mt-1 text-slate-800">
                          {a.transcript_fr || "—"}
                          {a.lang && <span className="ml-1 text-[11px] text-slate-400"><Languages size={10} className="inline" /> {a.lang}</span>}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-1 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                <Camera size={13} /> Photos reçues ({photos.length})
              </div>
              <div className="flex flex-wrap gap-2">
                {cats.map((c) => (
                  <span key={c.key} className={`text-xs px-2 py-1 rounded-full border ${photoCounts[c.key] ? "bg-[#0F2B48] text-white border-[#0F2B48]" : "bg-slate-50 text-slate-500 border-slate-200"}`} data-testid={`amorce-cat-${c.key}`}>
                    {c.label}{photoCounts[c.key] ? ` · ${photoCounts[c.key]}` : ""}
                  </span>
                ))}
              </div>
              {session.declarations && session.declarations.no_job_posting && (
                <p className="mt-2 text-[12px] text-slate-500">✓ Déclaré : aucune offre d'emploi active.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {session && !isActive && (
        <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 flex items-center justify-between gap-3" data-testid="amorce-inactive">
          <p className="text-sm text-slate-600">
            {session.status === "completed" && `Amorce complétée — ${Object.keys(answers).length} réponse(s), ${photos.length} photo(s) au dossier.`}
            {session.status === "expired" && "Le dernier lien QR a expiré."}
            {session.status === "revoked" && "Le dernier lien QR a été révoqué."}
          </p>
          <Button onClick={generate} disabled={busy} variant="outline" data-testid="amorce-regenerate">
            <RefreshCw size={14} className="mr-1" /> Nouveau lien
          </Button>
        </div>
      )}
    </Card>
  );
};
