import { useMemo, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { AlertTriangle, X, Save, Info } from "lucide-react";
import { GanttGrid, effectiveDates, isoDate, startOfToday } from "@/components/GanttGrid";

// Couleurs par statut de mise en œuvre (RMO)
const STATUT_BAR = {
  a_faire: "bg-slate-400",
  en_cours: "bg-blue-500",
  completee: "bg-emerald-500",
  reportee: "bg-amber-400",
};
const STATUT_LABEL = {
  a_faire: "À faire", en_cours: "En cours", completee: "Complétée", reportee: "Reportée",
};

function BarEditor({ dossier, mesure, label, onUpdated, onClose }) {
  const today = useMemo(startOfToday, []);
  const eff = effectiveDates(mesure, today, "date_debut", "echeance");
  const [debut, setDebut] = useState(mesure?.date_debut || isoDate(eff.debut));
  const [echeance, setEcheance] = useState(mesure?.echeance || isoDate(eff.echeance));
  const [inc, setInc] = useState(!!mesure?.incontournable);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      const mesures = (dossier.module2_mesures || []).map((m) =>
        m.id === mesure.id ? { ...m, date_debut: debut, echeance, incontournable: inc } : m);
      const { data } = await api.patch(`/dossiers/${dossier.id}/module2`, {
        module2_admin: dossier.module2_admin || {}, module2_mesures: mesures });
      toast.success("Échéancier enregistré");
      onUpdated(data); onClose();
    } catch (e) { toast.error("Erreur"); } finally { setBusy(false); }
  };

  return (
    <Card className="p-4 space-y-3" data-testid={`gantt-fr-editor-${mesure.id}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">{mesure.theme_id}</span>
          <h4 className="font-display font-bold text-[#0F2B48] mt-1">{label}</h4>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700" data-testid="gantt-fr-editor-close"><X size={18} /></button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1"><Label className="text-xs">Début</Label>
          <Input type="date" value={debut} onChange={(e) => setDebut(e.target.value)} data-testid={`gantt-fr-debut-${mesure.id}`} /></div>
        <div className="space-y-1"><Label className="text-xs">Échéance</Label>
          <Input type="date" value={echeance} onChange={(e) => setEcheance(e.target.value)} data-testid={`gantt-fr-echeance-${mesure.id}`} /></div>
      </div>
      <label className="flex items-center gap-2 text-sm text-slate-600">
        <input type="checkbox" checked={inc} onChange={(e) => setInc(e.target.checked)} data-testid={`gantt-fr-inc-${mesure.id}`} />
        <AlertTriangle size={14} className="text-red-600" /> Échéance incontournable (délai légal / OQLF)
      </label>
      <Button size="sm" onClick={save} disabled={busy} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid={`gantt-fr-save-${mesure.id}`}>
        <Save size={14} className="mr-1" /> Enregistrer l'échéancier
      </Button>
    </Card>
  );
}

export const GanttFrancisation = ({ dossier, themes = [], onUpdated }) => {
  const [selected, setSelected] = useState(null);
  const today = useMemo(startOfToday, []);
  const mesures = dossier.module2_mesures || [];
  const themeName = (id) => themes.find((t) => t.id === id)?.nom_theme || id;

  const rows = useMemo(() => mesures.map((m, i) => {
    const eff = effectiveDates(m, today, "date_debut", "echeance");
    const label = (m.mesure_engagee || "").trim() || `${themeName(m.theme_id)} — mesure ${i + 1}`;
    return {
      code: m.id, badge: m.theme_id, label,
      statut: m.statut_mise_en_oeuvre || "a_faire", incontournable: !!m.incontournable,
      planned: eff.planned, debut: eff.debut, echeance: eff.echeance,
    };
  }), [mesures, themes, today]);

  const selMesure = mesures.find((m) => m.id === selected);
  const selLabel = rows.find((r) => r.code === selected)?.label;

  if (!mesures.length) {
    return (
      <Card className="p-6 flex items-start gap-2 bg-blue-50/60 border-blue-200" data-testid="gantt-fr-empty">
        <Info size={16} className="text-blue-700 mt-0.5" />
        <p className="text-sm text-blue-800">Aucune mesure de francisation enregistrée. Ajoutez des mesures dans l'onglet <b>Programme</b> (Niveau A / Niveau B) et enregistrez-les, puis revenez ici pour visualiser leur échéancier.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4" data-testid="gantt-francisation">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="text-[11px] font-semibold text-slate-600">Échéancier des mesures de francisation — {rows.length} mesure(s)</span>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
          {Object.entries(STATUT_LABEL).map(([k, v]) => (
            <span key={k} className="flex items-center gap-1"><span className={`inline-block h-3 w-4 rounded ${STATUT_BAR[k]}`} /> {v}</span>
          ))}
          <span className="flex items-center gap-1"><span className="inline-block h-3 w-4 rounded ring-2 ring-red-500 bg-red-500" /> incontournable</span>
          <span className="flex items-center gap-1"><span className="inline-block h-4 w-0.5 bg-red-500" /> aujourd'hui</span>
        </div>
      </div>
      <GanttGrid rows={rows} statutColors={STATUT_BAR} onSelect={setSelected} testId="gantt-fr-grid" />
      {selMesure && (
        <BarEditor dossier={dossier} mesure={selMesure} label={selLabel} onUpdated={onUpdated} onClose={() => setSelected(null)} />
      )}
      <p className="text-[11px] text-slate-400">Cliquez sur une barre pour fixer les dates de début et d'échéance de la mesure. Les mesures non planifiées affichent une échéance provisoire à +3 mois. La couleur reflète le statut de mise en œuvre (RMO).</p>
    </div>
  );
};
