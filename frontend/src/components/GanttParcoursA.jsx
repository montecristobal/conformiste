import { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Loader2, AlertTriangle, X, Save } from "lucide-react";

const STATUT_BAR = {
  non_evalue: "bg-slate-300",
  conforme: "bg-emerald-500",
  a_valider: "bg-amber-400",
  non_conforme: "bg-red-500",
  sans_objet: "bg-slate-200",
};
const STATUT_LABEL = {
  non_evalue: "Non évalué", conforme: "Conforme", a_valider: "À valider",
  non_conforme: "Non conforme", sans_objet: "Sans objet",
};

const DAY = 86400000;
const iso = (d) => d.toISOString().slice(0, 10);
const parseD = (s) => (s ? new Date(s + "T00:00:00") : null);
const mondayOf = (d) => { const x = new Date(d); const day = (x.getDay() + 6) % 7; x.setDate(x.getDate() - day); x.setHours(0, 0, 0, 0); return x; };
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const addMonths = (d, n) => { const x = new Date(d); x.setMonth(x.getMonth() + n); return x; };

// Résout dates effectives (défaut aujourd'hui → +3 mois si non planifié)
function effectiveDates(saved, today) {
  const planned = !!(saved?.date_debut || saved?.date_echeance);
  const debut = parseD(saved?.date_debut) || today;
  const echeance = parseD(saved?.date_echeance) || addMonths(debut, 3);
  return { planned, debut, echeance };
}

function BarEditor({ dossierId, code, label, saved, onUpdated, onClose }) {
  const today = useMemo(() => { const t = new Date(); t.setHours(0, 0, 0, 0); return t; }, []);
  const eff = effectiveDates(saved, today);
  const [debut, setDebut] = useState(saved?.date_debut || iso(eff.debut));
  const [echeance, setEcheance] = useState(saved?.date_echeance || iso(eff.echeance));
  const [inc, setInc] = useState(!!saved?.incontournable);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.patch(`/dossiers/${dossierId}/parcours-a/element/${code}`,
        { date_debut: debut, date_echeance: echeance, incontournable: inc });
      toast.success("Échéancier enregistré");
      onUpdated(data); onClose();
    } catch (e) { toast.error("Erreur"); } finally { setBusy(false); }
  };

  return (
    <Card className="p-4 space-y-3" data-testid={`gantt-editor-${code}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">{code}</span>
          <h4 className="font-display font-bold text-[#0F2B48] mt-1">{label}</h4>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700" data-testid="gantt-editor-close"><X size={18} /></button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1"><Label className="text-xs">Début</Label>
          <Input type="date" value={debut} onChange={(e) => setDebut(e.target.value)} data-testid={`gantt-debut-${code}`} /></div>
        <div className="space-y-1"><Label className="text-xs">Échéance</Label>
          <Input type="date" value={echeance} onChange={(e) => setEcheance(e.target.value)} data-testid={`gantt-echeance-${code}`} /></div>
      </div>
      <label className="flex items-center gap-2 text-sm text-slate-600">
        <input type="checkbox" checked={inc} onChange={(e) => setInc(e.target.checked)} data-testid={`gantt-inc-${code}`} />
        <AlertTriangle size={14} className="text-red-600" /> Échéance incontournable (délai légal)
      </label>
      <Button size="sm" onClick={save} disabled={busy} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid={`gantt-save-${code}`}>
        <Save size={14} className="mr-1" /> Enregistrer l'échéancier
      </Button>
    </Card>
  );
}

export const GanttParcoursA = ({ dossier, onUpdated }) => {
  const [themes, setThemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const els = dossier.parcours_a_elements || {};
  const today = useMemo(() => { const t = new Date(); t.setHours(0, 0, 0, 0); return t; }, []);

  useEffect(() => {
    setLoading(true);
    api.get("/catalogue/themes?regime=A")
      .then(({ data }) => setThemes(data)).catch(() => {}).finally(() => setLoading(false));
  }, [dossier.id]);

  // Construit la liste des éléments (U1–U18 + REQ) avec dates effectives
  const rows = useMemo(() => {
    const ordered = [...themes].sort((a, b) =>
      (a.prioritaire_amorce === b.prioritaire_amorce) ? a.ordre - b.ordre : (a.prioritaire_amorce ? -1 : 1));
    const list = ordered.map((t) => {
      const saved = els[t.id];
      const eff = effectiveDates(saved, today);
      return {
        code: t.id, label: t.nom_theme, article: t.article, saved,
        statut: saved?.statut || "non_evalue",
        incontournable: !!saved?.incontournable,
        planned: eff.planned, debut: eff.debut, echeance: eff.echeance,
      };
    });
    if (dossier.req_declaration_requise) {
      const saved = els["REQ"];
      const eff = effectiveDates(saved, today);
      list.push({
        code: "REQ", label: "Déclaration au registraire des entreprises (REQ)", article: "Charte, art. 149–152.1",
        saved, statut: saved?.statut || "non_evalue",
        incontournable: saved?.incontournable != null ? !!saved.incontournable : true,
        planned: eff.planned, debut: eff.debut, echeance: eff.echeance,
      });
    }
    return list;
  }, [themes, els, dossier.req_declaration_requise, today]);

  const { start, end, weeks } = useMemo(() => {
    if (!rows.length) return { start: today, end: addMonths(today, 3), weeks: [] };
    let mn = today, mx = addMonths(today, 3);
    rows.forEach((r) => { if (r.debut < mn) mn = r.debut; if (r.echeance > mx) mx = r.echeance; });
    const s = mondayOf(mn);
    const e = addDays(mondayOf(mx), 7);
    const w = [];
    for (let cur = new Date(s); cur < e; cur = addDays(cur, 7)) w.push(new Date(cur));
    return { start: s, end: e, weeks: w };
  }, [rows, today]);

  if (loading) return <div className="flex items-center gap-2 text-slate-400 p-8"><Loader2 className="animate-spin" size={18} /> Chargement…</div>;

  const totalDays = Math.max(1, (end - start) / DAY);
  const pct = (d) => ((d - start) / DAY / totalDays) * 100;
  const todayPct = pct(today);
  const colW = 64; // px par semaine
  const gridW = weeks.length * colW;
  const selRow = rows.find((r) => r.code === selected);

  return (
    <div className="space-y-4" data-testid="gantt-parcoursa">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-slate-500">
        <span className="font-semibold text-slate-600">Échéancier de mise en conformité — {rows.length} éléments</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-4 rounded bg-indigo-500" /> planifié</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-4 rounded border-2 border-dashed border-slate-300 bg-slate-100" /> provisoire (+3 mois par défaut)</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-4 rounded ring-2 ring-red-500 bg-red-500" /> incontournable</span>
        <span className="flex items-center gap-1"><span className="inline-block h-4 w-0.5 bg-red-500" /> aujourd'hui</span>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white overflow-x-auto" data-testid="gantt-scroll">
        <div className="flex" style={{ minWidth: 240 + gridW }}>
          {/* Colonne des libellés */}
          <div className="w-60 shrink-0 border-r border-slate-200">
            <div className="h-9 border-b border-slate-200 bg-slate-50 flex items-center px-3 text-[11px] font-semibold text-slate-500">Élément</div>
            {rows.map((r) => (
              <button key={r.code} onClick={() => setSelected(r.code)} data-testid={`gantt-row-label-${r.code}`}
                className="h-10 w-full border-b border-slate-100 flex items-center gap-2 px-3 text-left hover:bg-indigo-50">
                <span className="text-[10px] font-mono font-semibold px-1 rounded bg-indigo-100 text-indigo-700 shrink-0">{r.code}</span>
                <span className="text-xs text-[#0F2B48] truncate">{r.label}</span>
              </button>
            ))}
          </div>

          {/* Zone du diagramme */}
          <div className="relative" style={{ width: gridW }}>
            {/* En-tête semaines */}
            <div className="h-9 border-b border-slate-200 bg-slate-50 flex">
              {weeks.map((w, i) => (
                <div key={i} className="border-r border-slate-100 flex flex-col items-center justify-center text-[9px] text-slate-400 leading-none" style={{ width: colW }}>
                  <span className="font-semibold text-slate-500">{w.toLocaleDateString("fr-CA", { day: "2-digit", month: "2-digit" })}</span>
                  <span>sem.</span>
                </div>
              ))}
            </div>
            {/* Lignes / barres */}
            <div className="relative">
              {/* quadrillage vertical */}
              <div className="absolute inset-0 flex pointer-events-none">
                {weeks.map((_, i) => <div key={i} className="border-r border-slate-100" style={{ width: colW }} />)}
              </div>
              {/* ligne aujourd'hui */}
              {todayPct >= 0 && todayPct <= 100 && (
                <div className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10" style={{ left: `${todayPct}%` }} data-testid="gantt-today-line" />
              )}
              {rows.map((r) => {
                const left = pct(r.debut);
                const width = Math.max(1.5, pct(r.echeance) - left);
                const barCls = r.incontournable ? "bg-red-500 ring-2 ring-red-600"
                  : (STATUT_BAR[r.statut] || "bg-indigo-500");
                const provisoire = !r.planned;
                return (
                  <div key={r.code} className="h-10 border-b border-slate-100 relative">
                    <button onClick={() => setSelected(r.code)} data-testid={`gantt-bar-${r.code}`}
                      title={`${r.label} — ${iso(r.debut)} → ${iso(r.echeance)}`}
                      className={`absolute top-1.5 h-7 rounded-md ${barCls} ${provisoire ? "opacity-60 border-2 border-dashed border-slate-400" : ""} hover:brightness-110 transition-all flex items-center px-1.5`}
                      style={{ left: `${left}%`, width: `${width}%`, minWidth: 18 }}>
                      {r.incontournable && <AlertTriangle size={11} className="text-white shrink-0" />}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {selRow && (
        <BarEditor dossierId={dossier.id} code={selRow.code} label={selRow.label} saved={selRow.saved}
          onUpdated={onUpdated} onClose={() => setSelected(null)} />
      )}
      <p className="text-[11px] text-slate-400">Cliquez sur une barre ou un libellé pour fixer les dates de début et d'échéance. Les éléments non planifiés affichent une échéance provisoire à +3 mois.</p>
    </div>
  );
};
