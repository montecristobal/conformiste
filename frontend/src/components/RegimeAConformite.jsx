import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Info, ChevronDown, ChevronRight, ScanSearch, Check, AlertTriangle, ShieldQuestion,
  Minus, Loader2,
} from "lucide-react";

const STAT = {
  conforme: { text: "text-emerald-700", bg: "bg-emerald-100", icon: Check, label: "Conforme" },
  non_conforme: { text: "text-red-700", bg: "bg-red-100", icon: AlertTriangle, label: "Non conforme" },
  a_valider: { text: "text-amber-700", bg: "bg-amber-100", icon: ShieldQuestion, label: "À valider" },
  non_evalue: { text: "text-slate-500", bg: "bg-slate-100", icon: Minus, label: "Non évalué" },
};

function themeStatus(findings) {
  if (!findings || findings.length === 0) return "non_evalue";
  if (findings.some((f) => f.statut === "non_conforme")) return "non_conforme";
  return "a_valider";
}

function ThemeCard({ theme, findings }) {
  const [open, setOpen] = useState(false);
  const st = STAT[themeStatus(findings)];
  const Icon = st.icon;
  return (
    <Card className="p-4" data-testid={`regimea-theme-${theme.id}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded bg-[#0F2B48] text-white">{theme.id}</span>
            <span className="text-[11px] text-slate-500">{theme.article}</span>
            {!theme.prioritaire_amorce && (
              <span className="text-[10px] text-slate-400 border border-slate-200 rounded-full px-2 py-0.5">cas marginal</span>
            )}
          </div>
          <h4 className="font-display font-bold text-[#0F2B48] mt-1 leading-snug">{theme.nom_theme}</h4>
        </div>
        <span className={`shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold ${st.text} ${st.bg}`} data-testid={`regimea-status-${theme.id}`}>
          <Icon size={12} /> {st.label}
        </span>
      </div>

      {findings && findings.length > 0 && (
        <ul className="mt-3 space-y-2">
          {findings.map((f) => (
            <li key={f.finding_id} className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2 text-sm" data-testid={`regimea-finding-${f.finding_id}`}>
              <p className="text-slate-700">{f.constat}</p>
              {f.mesure_suggeree && <p className="text-xs text-slate-600 mt-1"><b>Mesure suggérée :</b> {f.mesure_suggeree}</p>}
              <p className="text-[10px] text-slate-400 mt-1 truncate">Source : {f.source}</p>
            </li>
          ))}
        </ul>
      )}

      <button onClick={() => setOpen((o) => !o)} className="mt-3 flex items-center gap-1 text-xs text-[#2563EB] hover:underline" data-testid={`regimea-toggle-${theme.id}`}>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />} {open ? "Masquer" : "Voir"} le texte de loi
      </button>
      {open && (
        <div className="mt-2 rounded-lg bg-slate-50 border border-slate-100 p-3">
          <p className="text-[13px] text-slate-600 whitespace-pre-line">{theme.texte_loi || "Texte non disponible."}</p>
          {theme.external_citation && <p className="text-[11px] text-slate-400 mt-2">{theme.external_citation}</p>}
        </div>
      )}
    </Card>
  );
}

export const RegimeAConformite = ({ dossier, onGoAnalyse }) => {
  const [themes, setThemes] = useState([]);
  const [plan, setPlan] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get("/catalogue/themes?regime=A"),
      api.get(`/dossiers/${dossier.id}/plan-correction`),
    ])
      .then(([t, p]) => { setThemes(t.data); setPlan(p.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [dossier.id]);

  const byTheme = {};
  plan.forEach((f) => { (byTheme[f.theme_id] = byTheme[f.theme_id] || []).push(f); });

  const ordered = [...themes].sort((a, b) =>
    (a.prioritaire_amorce === b.prioritaire_amorce) ? a.ordre - b.ordre : (a.prioritaire_amorce ? -1 : 1));
  const evalues = ordered.filter((t) => (byTheme[t.id] || []).length > 0).length;

  if (loading) {
    return <div className="flex items-center gap-2 text-slate-400 p-8" data-testid="regimea-loading"><Loader2 className="animate-spin" size={18} /> Chargement du tableau de bord…</div>;
  }

  return (
    <div className="space-y-5" data-testid="regimea-conformite">
      <div className="flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-amber-800" data-testid="regimea-prudence">
        <Info size={16} className="mt-0.5 shrink-0" />
        <p className="text-sm">
          Estimation indicative — à valider par un professionnel. Entreprise de <b>moins de 25 employés</b> :
          seules les <b>obligations universelles</b> de la Charte s'appliquent (aucun parcours de francisation, aucun certificat).
        </p>
      </div>

      <Card className="p-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-display text-lg font-bold text-[#0F2B48]">Conformité aux obligations universelles</h3>
          <p className="text-sm text-slate-500">
            {evalues} thème(s) évalué(s) sur {ordered.length}. Téléversez des documents ou lancez l'amorce mobile pour alimenter l'analyse.
          </p>
        </div>
        <Button onClick={onGoAnalyse} className="bg-[#2563EB] hover:bg-[#2563EB]/90" data-testid="regimea-go-analyse">
          <ScanSearch size={16} className="mr-2" /> Analyser des documents
        </Button>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {ordered.map((t) => (
          <ThemeCard key={t.id} theme={t} findings={byTheme[t.id]} />
        ))}
      </div>
    </div>
  );
};
