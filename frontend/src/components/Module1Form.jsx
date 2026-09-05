import { useState, useMemo, useEffect } from "react";
import { MODULE1_SECTIONS } from "@/data/module1Schema";
import { FieldRenderer } from "@/components/FieldRenderer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";
import { Save, FileDown, CheckCircle2, Info, Sparkles } from "lucide-react";
import api, { API, downloadPdf } from "@/lib/api";
import { WebEnrichPanel } from "@/components/WebEnrichPanel";

export function Module1Form({ dossier, onSaved }) {
  const [values, setValues] = useState(dossier.module1_data || {});
  const [activeSection, setActiveSection] = useState("s1");
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [enrichBusy, setEnrichBusy] = useState(false);
  const [proposals, setProposals] = useState(null);
  const [enrichMeta, setEnrichMeta] = useState({});

  useEffect(() => { setValues(dossier.module1_data || {}); }, [dossier.id]);

  const runEnrich = async () => {
    setEnrichBusy(true);
    try {
      const site = values["s1.sites_web"] || dossier.oqlf_data?.site_web || "";
      const { data } = await api.post(`/dossiers/${dossier.id}/module1/enrich`, { site_url: site });
      setProposals(data.proposals || []);
      setEnrichMeta({ site_used: data.site_used || [], warnings: data.warnings || [] });
      if ((data.proposals || []).length === 0) toast.info("Aucune proposition trouvée");
    } catch (e) {
      toast.error("Recherche Web impossible");
    } finally { setEnrichBusy(false); }
  };

  const applyProposals = (map) => {
    const n = Object.keys(map).length;
    setValues((p) => ({ ...p, ...map }));
    setProposals(null);
    if (n > 0) toast.success(`${n} champ(s) pré-rempli(s) — pensez à enregistrer`);
  };

  const employes = Number(values["s4.employes_quebec"] ?? dossier.nb_employes_quebec ?? 0);
  const etablissements = Number(values["s4.etablissements"] ?? dossier.nb_etablissements ?? 1);

  const sections = useMemo(() => MODULE1_SECTIONS.filter((s) => {
    if (s.condition === "annexe1") return employes >= 100;
    if (s.condition === "annexe2") return etablissements > 1;
    return true;
  }), [employes, etablissements]);

  const onChange = (key, v) => setValues((p) => ({ ...p, [key]: v }));

  const sectionCompletion = (sec) => {
    const keys = sec.fields.map((f) => `${sec.id}.${f.id}`);
    const filled = keys.filter((k) => {
      const v = values[k];
      return v !== undefined && v !== "" && !(Array.isArray(v) && v.length === 0);
    }).length;
    return Math.round((filled / keys.length) * 100);
  };

  const save = async () => {
    setSaving(true);
    try {
      const labels = {};
      const secMeta = sections.map((sec) => {
        const field_keys = sec.fields.map((f) => `${sec.id}.${f.id}`);
        sec.fields.forEach((f) => { labels[`${sec.id}.${f.id}`] = f.label; });
        return { id: sec.id, titre: sec.titre, field_keys };
      });
      const { data } = await api.patch(`/dossiers/${dossier.id}/module1`, {
        module1_data: values,
        module1_meta: { sections: secMeta, labels },
      });
      setLastSaved(new Date());
      toast.success("Module 1 enregistré");
      onSaved?.(data);
    } catch (e) {
      toast.error("Erreur lors de l'enregistrement");
    } finally { setSaving(false); }
  };

  const exportPdf = () => {
    downloadPdf(`/dossiers/${dossier.id}/export/module1`, `analyse_linguistique_${dossier.neq || dossier.id}.pdf`)
      .catch(() => toast.error("Erreur lors de l'export PDF"));
  };

  const active = sections.find((s) => s.id === activeSection) || sections[0];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6">
      <aside className="lg:sticky lg:top-24 h-fit space-y-1">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-slate-700">Sections</h4>
          {lastSaved && (
            <span className="text-[10px] text-green-600 flex items-center gap-1">
              <CheckCircle2 size={11} /> {lastSaved.toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </div>
        {sections.map((s) => {
          const pct = sectionCompletion(s);
          const isActive = s.id === active.id;
          return (
            <button key={s.id} data-testid={`m1-nav-${s.id}`} onClick={() => setActiveSection(s.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                isActive ? "bg-[#0F2B48] text-white" : "hover:bg-slate-100 text-slate-600"
              }`}>
              <div className="flex items-center justify-between gap-2">
                <span className="line-clamp-2">{s.titre}</span>
                <span className={`text-[10px] font-mono ${isActive ? "text-blue-200" : pct === 100 ? "text-green-600" : "text-slate-400"}`}>{pct}%</span>
              </div>
            </button>
          );
        })}
      </aside>

      <div className="space-y-4">
        <Card className="p-3 flex flex-wrap items-center justify-between gap-3 bg-blue-50/60 border-blue-200">
          <div className="flex items-center gap-2 text-xs text-blue-800">
            <Info size={15} />
            {dossier.echeance_module1
              ? <span>Échéance légale : <b>{dossier.echeance_module1}</b> ({dossier.jours_restants_module1} jours) — 3 mois après l'attestation d'inscription.</span>
              : <span>Saisissez la date d'attestation d'inscription pour calculer l'échéance légale.</span>}
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={runEnrich} disabled={enrichBusy} data-testid="module1-enrich-button"
              className="border-emerald-300 text-emerald-800 hover:bg-emerald-50">
              <Sparkles size={15} className="mr-1" /> {enrichBusy ? "Recherche…" : "Pré-remplir par recherche Web"}
            </Button>
            <Button size="sm" variant="outline" onClick={exportPdf} data-testid="export-pdf-module1-button">
              <FileDown size={15} className="mr-1" /> Export PDF
            </Button>
            <Button size="sm" onClick={save} disabled={saving} data-testid="module1-save-button"
              className="bg-[#0F2B48] hover:bg-[#0F2B48]/90">
              <Save size={15} className="mr-1" /> {saving ? "Enregistrement…" : "Enregistrer"}
            </Button>
          </div>
        </Card>

        {proposals !== null && (
          <WebEnrichPanel proposals={proposals} meta={enrichMeta}
            onApply={applyProposals} onClose={() => setProposals(null)} />
        )}

        <Card className="p-6" data-testid={`m1-section-${active.id}`}>
          <h3 className="font-display text-lg font-bold text-[#0F2B48] mb-5">{active.titre}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {active.fields.map((f) => (
              <div key={f.id} className={f.type === "table" || f.type === "textarea" ? "md:col-span-2" : ""}>
                <FieldRenderer field={f} sectionId={active.id} values={values} onChange={onChange} dossierId={dossier.id} />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
