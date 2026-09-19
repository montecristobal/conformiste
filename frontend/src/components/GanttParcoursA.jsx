import { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Loader2, AlertTriangle, X, Save } from "lucide-react";
import { GanttGrid, effectiveDates, isoDate, startOfToday } from "@/components/GanttGrid";
import { ExportGanttButton } from "@/components/ExportGanttButton";

const STATUT_BAR = {
  non_evalue: "bg-slate-300",
  conforme: "bg-emerald-500",
  a_valider: "bg-amber-400",
  non_conforme: "bg-red-500",
  sans_objet: "bg-slate-200",
};

function BarEditor({ dossierId, code, label, saved, onUpdated, onClose }) {
  const today = useMemo(startOfToday, []);
  const eff = effectiveDates(saved, today);
  const [debut, setDebut] = useState(saved?.date_debut || isoDate(eff.debut));
  const [echeance, setEcheance] = useState(saved?.date_echeance || isoDate(eff.echeance));
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

const Legend = () => (
  <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-slate-500">
    <span className="flex items-center gap-1"><span className="inline-block h-3 w-4 rounded bg-indigo-500" /> planifié</span>
    <span className="flex items-center gap-1"><span className="inline-block h-3 w-4 rounded border-2 border-dashed border-slate-300 bg-slate-100" /> provisoire (+3 mois par défaut)</span>
    <span className="flex items-center gap-1"><span className="inline-block h-3 w-4 rounded ring-2 ring-red-500 bg-red-500" /> incontournable</span>
    <span className="flex items-center gap-1"><span className="inline-block h-4 w-0.5 bg-red-500" /> aujourd'hui</span>
  </div>
);

export const GanttParcoursA = ({ dossier, onUpdated }) => {
  const [themes, setThemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const els = dossier.parcours_a_elements || {};
  const today = useMemo(startOfToday, []);

  useEffect(() => {
    setLoading(true);
    api.get("/catalogue/themes?regime=A")
      .then(({ data }) => setThemes(data)).catch(() => {}).finally(() => setLoading(false));
  }, [dossier.id]);

  const rows = useMemo(() => {
    const applicable = dossier.parcours_a_applicable;
    const applicableSet = applicable ? new Set(applicable) : null;
    const ordered = [...themes]
      .filter((t) => !applicableSet || applicableSet.has(t.id))
      .sort((a, b) =>
        (a.prioritaire_amorce === b.prioritaire_amorce) ? a.ordre - b.ordre : (a.prioritaire_amorce ? -1 : 1));
    const list = ordered.map((t) => {
      const saved = els[t.id];
      const eff = effectiveDates(saved, today);
      return {
        code: t.id, badge: t.id, label: t.nom_theme, saved,
        statut: saved?.statut || "non_evalue", incontournable: !!saved?.incontournable,
        planned: eff.planned, debut: eff.debut, echeance: eff.echeance,
      };
    });
    if (dossier.req_declaration_requise) {
      const saved = els["REQ"];
      const eff = effectiveDates(saved, today);
      list.push({
        code: "REQ", badge: "REQ", label: "Déclaration au registraire des entreprises (REQ)", saved,
        statut: saved?.statut || "non_evalue",
        incontournable: saved?.incontournable != null ? !!saved.incontournable : true,
        planned: eff.planned, debut: eff.debut, echeance: eff.echeance,
      });
    }
    return list;
  }, [themes, els, dossier.req_declaration_requise, dossier.parcours_a_applicable, today]);

  if (loading) return <div className="flex items-center gap-2 text-slate-400 p-8"><Loader2 className="animate-spin" size={18} /> Chargement…</div>;

  const selRow = rows.find((r) => r.code === selected);

  return (
    <div className="space-y-4" data-testid="gantt-parcoursa">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="text-[11px] font-semibold text-slate-600">Échéancier de mise en conformité — {rows.length} éléments</span>
          <Legend />
        </div>
        <ExportGanttButton dossierId={dossier.id} kind="parcours_a" />
      </div>
      <GanttGrid rows={rows} statutColors={STATUT_BAR} onSelect={setSelected} testId="gantt-parcoursa-grid" />
      {selRow && (
        <BarEditor dossierId={dossier.id} code={selRow.code} label={selRow.label} saved={selRow.saved}
          onUpdated={onUpdated} onClose={() => setSelected(null)} />
      )}
      <p className="text-[11px] text-slate-400">Cliquez sur une barre ou un libellé pour fixer les dates de début et d'échéance. Les éléments non planifiés affichent une échéance provisoire à +3 mois.</p>
    </div>
  );
};
