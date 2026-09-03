import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Save, FileDown, Plus, Trash2, Lock, Users, Info } from "lucide-react";
import api, { API, downloadPdf } from "@/lib/api";
import { v4 as uuidv4 } from "@/lib/uuid";

const STATUTS = [
  { value: "a_faire", label: "À faire" },
  { value: "en_cours", label: "En cours" },
  { value: "completee", label: "Complétée" },
  { value: "reportee", label: "Reportée" },
];

function MesureCard({ mesure, onChange, onRemove, index }) {
  const set = (k, v) => onChange({ ...mesure, [k]: v });
  const tid = `mesure-${mesure.id}`;
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4 space-y-3" data-testid={tid}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Mesure {index + 1}</span>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={onRemove} data-testid={`${tid}-remove`}>
          <Trash2 size={14} />
        </Button>
      </div>
      <div className="space-y-1.5">
        <Label className="text-xs">Mesure engagée</Label>
        <Textarea rows={2} value={mesure.mesure_engagee ?? ""} onChange={(e) => set("mesure_engagee", e.target.value)} data-testid={`${tid}-engagee`} />
      </div>
      <div className="space-y-1.5">
        <Label className="text-xs">Précisions de l'entreprise</Label>
        <Textarea rows={2} value={mesure.precisions_entreprise ?? ""} onChange={(e) => set("precisions_entreprise", e.target.value)} data-testid={`${tid}-precisions`} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label className="text-xs">Commentaire de l'Office (optionnel)</Label>
          <Input value={mesure.precisions_oqlf ?? ""} onChange={(e) => set("precisions_oqlf", e.target.value)} data-testid={`${tid}-oqlf-comm`} />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Proposition de l'Office (optionnel)</Label>
          <Input value={mesure.propositions_oqlf ?? ""} onChange={(e) => set("propositions_oqlf", e.target.value)} data-testid={`${tid}-oqlf-prop`} />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Échéance</Label>
          <Input type="date" value={mesure.echeance ?? ""} onChange={(e) => set("echeance", e.target.value)} data-testid={`${tid}-echeance`} />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Statut de mise en œuvre (RMO)</Label>
          <Select value={mesure.statut_mise_en_oeuvre ?? "a_faire"} onValueChange={(v) => set("statut_mise_en_oeuvre", v)}>
            <SelectTrigger data-testid={`${tid}-statut`}><SelectValue /></SelectTrigger>
            <SelectContent className="bg-white">
              {STATUTS.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
}

function ThemeBlock({ theme, mesures, onChangeMesures, echoNom }) {
  const add = () => onChangeMesures([...mesures, { id: uuidv4(), theme_id: theme.id, statut_mise_en_oeuvre: "a_faire" }]);
  const update = (m) => onChangeMesures(mesures.map((x) => (x.id === m.id ? m : x)));
  const remove = (id) => onChangeMesures(mesures.filter((x) => x.id !== id));
  return (
    <Card className="p-5 space-y-4" data-testid={`theme-block-${theme.id}`}>
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-[10px] font-semibold px-2 py-0.5 rounded bg-[#0F2B48] text-white">{theme.id}</span>
          <h4 className="font-display font-bold text-slate-800">{theme.nom_theme}</h4>
        </div>
        <div className="mt-2 flex items-start gap-2 rounded-md bg-slate-100 border border-slate-200 px-3 py-2">
          <Lock size={13} className="text-slate-400 mt-0.5 shrink-0" />
          <div className="text-xs text-slate-500">
            <div><b>Libellé OQLF :</b> {theme.libelle_oqlf}</div>
            <div className="italic mt-0.5">Texte de loi : {theme.texte_loi || "[à valider — placeholder]"}</div>
            {echoNom && <div className="mt-0.5 text-blue-600">↳ Écho du Niveau A : {echoNom}</div>}
          </div>
        </div>
      </div>
      <div className="space-y-3">
        {mesures.map((m, i) => (
          <MesureCard key={m.id} mesure={m} index={i} onChange={update} onRemove={() => remove(m.id)} />
        ))}
      </div>
      <Button variant="outline" size="sm" onClick={add} data-testid={`module2-add-measure-${theme.id}`}>
        <Plus size={15} className="mr-1" /> Ajouter une mesure
      </Button>
    </Card>
  );
}

export function Module2Programme({ dossier, themes, onSaved }) {
  const [admin, setAdmin] = useState(dossier.module2_admin || {});
  const [mesures, setMesures] = useState(dossier.module2_mesures || []);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setAdmin(dossier.module2_admin || {});
    setMesures(dossier.module2_mesures || []);
  }, [dossier.id]);

  const themeMesures = (tid) => mesures.filter((m) => m.theme_id === tid);
  const setThemeMesures = (tid, list) => setMesures([...mesures.filter((m) => m.theme_id !== tid), ...list]);
  const themeName = (id) => themes.find((t) => t.id === id)?.nom_theme;

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.patch(`/dossiers/${dossier.id}/module2`, {
        module2_admin: admin, module2_mesures: mesures,
      });
      toast.success("Module 2 enregistré");
      onSaved?.(data);
    } catch (e) {
      toast.error("Erreur lors de l'enregistrement");
    } finally { setSaving(false); }
  };

  const niveauA = themes.filter((t) => t.niveau === "A");
  const niveauB = themes.filter((t) => t.niveau === "B");

  return (
    <div className="space-y-5">
      <Card className="p-3 flex flex-wrap items-center justify-between gap-3 bg-blue-50/60 border-blue-200">
        <div className="flex items-center gap-2 text-xs text-blue-800">
          <Info size={15} /> Catalogue légal fixe — ajoutez un nombre variable de mesures par thème. Structure réutilisée par le RMO.
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => downloadPdf(`/dossiers/${dossier.id}/export/module2`, `programme_francisation_${dossier.neq || dossier.id}.pdf`).catch(() => toast.error("Erreur lors de l'export PDF"))} data-testid="export-pdf-module2-button">
            <FileDown size={15} className="mr-1" /> Export PDF
          </Button>
          <Button size="sm" onClick={save} disabled={saving} data-testid="module2-save-button" className="bg-[#0F2B48] hover:bg-[#0F2B48]/90">
            <Save size={15} className="mr-1" /> {saving ? "Enregistrement…" : "Enregistrer"}
          </Button>
        </div>
      </Card>

      <Card className="p-5">
        <h4 className="font-display font-bold text-[#0F2B48] mb-4">Structure administrative</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label className="text-xs">Numéro de dossier OQLF</Label>
            <Input value={admin.numero_dossier_oqlf ?? ""} onChange={(e) => setAdmin({ ...admin, numero_dossier_oqlf: e.target.value })} data-testid="m2-numero-dossier" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Numéro de prolongation (le cas échéant)</Label>
            <Input value={admin.numero_prolongation ?? ""} onChange={(e) => setAdmin({ ...admin, numero_prolongation: e.target.value })} data-testid="m2-numero-prolongation" />
          </div>
        </div>
        {dossier.comite_requis && (
          <div className="mt-4 flex items-start gap-2 rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800" data-testid="m2-comite-block">
            <Users size={14} className="mt-0.5" />
            <span>Comité de francisation requis (100 employés ou plus). La section des signatures des membres reprend la structure de l'Annexe I du Module 1.</span>
          </div>
        )}
      </Card>

      <div>
        <h3 className="font-display text-lg font-bold text-[#0F2B48] mb-3">Niveau A — Obligations exécutoires universelles</h3>
        <div className="space-y-4">
          {niveauA.map((t) => (
            <ThemeBlock key={t.id} theme={t} mesures={themeMesures(t.id)} onChangeMesures={(l) => setThemeMesures(t.id, l)} />
          ))}
        </div>
      </div>
      <div>
        <h3 className="font-display text-lg font-bold text-[#0F2B48] mb-3">Niveau B — Objectifs de généralisation (art. 141)</h3>
        <div className="space-y-4">
          {niveauB.map((t) => (
            <ThemeBlock key={t.id} theme={t} mesures={themeMesures(t.id)} onChangeMesures={(l) => setThemeMesures(t.id, l)} echoNom={themeName(t.theme_echo_id)} />
          ))}
        </div>
      </div>
    </div>
  );
}
