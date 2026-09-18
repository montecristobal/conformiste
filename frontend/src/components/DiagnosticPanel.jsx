import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ShieldQuestion, Check, X, Minus, Gauge, ScrollText, AlertTriangle, Info,
  Languages, ArrowRight, Loader2,
} from "lucide-react";

const BAND = {
  vert: { bg: "bg-emerald-50", ring: "ring-emerald-200", text: "text-emerald-700", dot: "bg-emerald-500", label: "Vert" },
  jaune: { bg: "bg-amber-50", ring: "ring-amber-200", text: "text-amber-700", dot: "bg-amber-500", label: "Jaune" },
  rouge: { bg: "bg-red-50", ring: "ring-red-200", text: "text-red-700", dot: "bg-red-500", label: "Rouge" },
  non_evalue: { bg: "bg-slate-50", ring: "ring-slate-200", text: "text-slate-600", dot: "bg-slate-400", label: "Non évalué" },
};
const RISK = {
  faible: { text: "text-emerald-700", bg: "bg-emerald-100", label: "Faible" },
  modere: { text: "text-amber-700", bg: "bg-amber-100", label: "Modéré" },
  eleve: { text: "text-red-700", bg: "bg-red-100", label: "Élevé" },
};
const STAT = {
  francais: { text: "text-emerald-700", bg: "bg-emerald-100", label: "En français" },
  non_francais: { text: "text-red-700", bg: "bg-red-100", label: "Non conforme" },
  non_evalue: { text: "text-slate-500", bg: "bg-slate-100", label: "Non évalué" },
};

const CondIcon = ({ ok }) =>
  ok === true ? <Check size={15} className="text-emerald-600" /> :
  ok === false ? <X size={15} className="text-slate-400" /> :
  <Minus size={15} className="text-slate-400" />;

const fmtFactor = (f) =>
  f.value === null || f.value === undefined ? "non renseigné" :
  f.unit === "%" ? `${Math.round(f.value)} %` : String(f.value);

export const DiagnosticPanel = ({ dossier, onComplete }) => {
  const [diag, setDiag] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/dossiers/${dossier.id}/diagnostic`)
      .then(({ data }) => setDiag(data))
      .catch(() => setDiag(null))
      .finally(() => setLoading(false));
  }, [dossier.id]);

  if (loading) {
    return <div className="flex items-center gap-2 text-slate-400 p-8" data-testid="diagnostic-loading"><Loader2 className="animate-spin" size={18} /> Calcul du diagnostic…</div>;
  }
  if (!diag) return <div className="text-slate-500 p-8">Diagnostic indisponible.</div>;

  const { ep, francisabilite, conformite, risque } = diag;
  const band = BAND[conformite.band] || BAND.non_evalue;
  const risk = RISK[risque.niveau] || RISK.modere;
  const rev = francisabilite.revenus_hors_quebec;
  const conformes = conformite.evalues - conformite.non_conformes;

  return (
    <div className="space-y-5" data-testid="diagnostic-panel">
      <div className="flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-amber-800" data-testid="diagnostic-prudence">
        <Info size={16} className="mt-0.5 shrink-0" />
        <p className="text-sm">{diag.prudence}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Francisabilité + EP */}
        <Card className="p-5 space-y-4" data-testid="diag-francisabilite">
          <h3 className="font-display font-bold text-[#0F2B48] flex items-center gap-2"><Gauge size={18} /> Francisabilité</h3>
          <p className="text-[13px] text-slate-500">{francisabilite.note}</p>

          <div>
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>Revenus hors Québec</span>
              <span data-testid="diag-rev-hors">{rev === null ? "non renseigné" : `${Math.round(rev)} %`}</span>
            </div>
            <div className="relative h-3 rounded-full bg-slate-100">
              <div className="absolute top-0 bottom-0 w-px bg-slate-400" style={{ left: `${francisabilite.seuil}%` }} />
              {rev !== null && (
                <div className="absolute -top-1 h-5 w-5 rounded-full bg-[#0F2B48] ring-2 ring-white shadow"
                     style={{ left: `calc(${Math.min(100, Math.max(0, rev))}% - 10px)` }} data-testid="diag-rev-cursor" />
              )}
            </div>
            <div className="flex justify-between text-[10px] text-slate-400 mt-1">
              <span>0 %</span><span>seuil {francisabilite.seuil} %</span><span>100 %</span>
            </div>
          </div>

          <ul className="space-y-1.5">
            {francisabilite.facteurs.map((f, i) => (
              <li key={i} className="flex items-start justify-between gap-3 text-sm" data-testid={`diag-facteur-${i}`}>
                <span className={f.principal ? "font-medium text-[#0F2B48]" : "text-slate-600"}>{f.label}</span>
                <span className="shrink-0 tabular-nums">{fmtFactor(f)}</span>
              </li>
            ))}
          </ul>

          <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-3" data-testid="diag-ep">
            <div className="flex items-center gap-2 text-indigo-900">
              <ShieldQuestion size={16} />
              <span className="text-[11px] font-semibold uppercase tracking-wide">Entente particulière (art. 144)</span>
            </div>
            <p className="mt-1 font-semibold text-[#0F2B48]" data-testid="diag-ep-label">{ep.label}</p>
            <p className="text-[13px] text-slate-600">{ep.explication}</p>
            <ul className="mt-2 space-y-1">
              {ep.conditions.map((c, i) => (
                <li key={i} className="flex items-start gap-2 text-[13px] text-slate-600">
                  <span className="mt-0.5"><CondIcon ok={c.ok} /></span>
                  <span>{c.label} <span className="text-slate-400">— {c.detail}</span></span>
                </li>
              ))}
            </ul>
          </div>
        </Card>

        {/* Conformité + Risque */}
        <div className="space-y-5">
          <Card className={`p-5 space-y-3 ring-1 ${band.ring} ${band.bg}`} data-testid="diag-conformite">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-bold text-[#0F2B48] flex items-center gap-2"><Languages size={18} /> Conformité linguistique</h3>
              <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${band.text} bg-white/70`} data-testid="diag-conf-band">
                <span className={`inline-block w-2 h-2 rounded-full mr-1 ${band.dot}`} />{band.label}
              </span>
            </div>
            <p className="text-[13px] text-slate-600" data-testid="diag-conf-coverage">
              {conformite.evalues === 0
                ? "Aucun élément évalué pour l'instant — complétez le dossier pour obtenir un verdict."
                : `${conformes} élément(s) conforme(s) · ${conformite.non_conformes} non conforme(s) · ${conformite.evalues} évalué(s) sur ${conformite.total} pertinents`}
            </p>
            <ul className="space-y-1.5">
              {conformite.elements.map((e) => {
                const st = STAT[e.statut] || STAT.non_evalue;
                return (
                  <li key={e.key} className="flex items-center justify-between gap-3 text-sm bg-white/60 rounded-lg px-3 py-1.5" data-testid={`diag-conf-el-${e.key}`}>
                    <span className="text-slate-700">{e.label}{e.important && <span className="ml-1 text-[10px] text-slate-400">(clé)</span>}</span>
                    <span className={`shrink-0 px-2 py-0.5 rounded-full text-[11px] font-semibold ${st.text} ${st.bg}`}>{st.label}</span>
                  </li>
                );
              })}
            </ul>
            <p className="text-[11px] text-slate-500">{conformite.note}</p>
          </Card>

          <Card className="p-5 space-y-3" data-testid="diag-risque">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-bold text-[#0F2B48] flex items-center gap-2"><AlertTriangle size={18} /> Risque</h3>
              <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${risk.text} ${risk.bg}`} data-testid="diag-risque-niveau">{risk.label}</span>
            </div>
            <ul className="space-y-1">
              {risque.facteurs.map((f, i) => (
                <li key={i} className="flex items-start gap-2 text-[13px] text-slate-600"><ScrollText size={13} className="mt-0.5 shrink-0 text-slate-400" />{f}</li>
              ))}
            </ul>
          </Card>
        </div>
      </div>

      <div className="flex justify-end">
        <Button onClick={onComplete} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid="diag-complete-btn">
          Compléter le dossier <ArrowRight size={16} className="ml-2" />
        </Button>
      </div>
    </div>
  );
};
