import { useState, useMemo, useEffect } from "react";
import { MODULE1_SECTIONS } from "@/data/module1Schema";
import { FieldRenderer } from "@/components/FieldRenderer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";
import { Save, FileDown, CheckCircle2, Info, Sparkles, Camera, ChevronLeft, ChevronRight, Mic } from "lucide-react";
import api, { API, downloadPdf } from "@/lib/api";
import { WebEnrichPanel } from "@/components/WebEnrichPanel";
import { Input } from "@/components/ui/input";

const _CIV = { "Madame": "Mme", "Monsieur": "M." };
const _GADM = { "Oui": "Oui entièrement", "Non ou en partie seulement": "Non ou partiel" };

function _splitVilleCp(s) {
  if (!s) return [undefined, undefined];
  const m = String(s).match(/([A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d)/);
  const cp = m ? m[1] : undefined;
  let ville = String(s).replace(m ? m[1] : "", "").replace(/\(Qu[ée]bec\)/i, "").replace(/[,;]+\s*$/, "").trim();
  return [ville || undefined, cp];
}

// Reprend les renseignements saisis à l'inscription (OQLF) pour préremplir l'analyse linguistique.
function inscriptionPrefill(oqlf) {
  if (!oqlf) return {};
  const [s1ville, s1cp] = _splitVilleCp(oqlf.etab_principal_ville_cp);
  const [s2ville, s2cp] = _splitVilleCp(oqlf.resp_ville_cp);
  const map = {
    "s1.nom": oqlf.nom_entreprise,
    "s1.autres_noms": oqlf.autres_noms,
    "s1.sites_web": oqlf.site_web,
    "s1.neq": oqlf.neq,
    "s1.adresse": oqlf.etab_principal_adresse,
    "s1.ville": s1ville,
    "s1.code_postal": s1cp,
    "s2.civilite": _CIV[oqlf.resp_civilite],
    "s2.prenom": oqlf.resp_prenom,
    "s2.nom": oqlf.resp_nom,
    "s2.titre": oqlf.resp_titre,
    "s2.courriel": oqlf.resp_courriel,
    "s2.telephone": oqlf.resp_telephone,
    "s2.poste": oqlf.resp_poste,
    "s2.adresse": oqlf.resp_adresse,
    "s2.ville": s2ville,
    "s2.code_postal": s2cp,
    "s3.activites": oqlf.activites_principales,
    "s4.employes_quebec": oqlf.nb_employes_actuel,
    "s4.etablissements": oqlf.nb_etablissements,
    "s4.siege_quebec": oqlf.siege_au_quebec,
    "s4.siege_ville": oqlf.siege_lieu,
    "s4.gestion_admin": _GADM[oqlf.gere_admin],
    "s4.gestion_admin_expl": oqlf.gere_admin_precision,
    "s4.centre_recherche": oqlf.centre_recherche,
    "s4.centre_domaines": oqlf.centre_recherche_domaines,
    "s4.etab_hors_quebec": oqlf.etab_hors_quebec,
  };
  const out = {};
  Object.entries(map).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") out[k] = v; });
  return out;
}

export function Module1Form({ dossier, onSaved }) {
  const [values, setValues] = useState(dossier.module1_data || {});
  const [activeSection, setActiveSection] = useState("s1");
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [enrichBusy, setEnrichBusy] = useState(false);
  const [proposals, setProposals] = useState(null);
  const [enrichMeta, setEnrichMeta] = useState({});
  const [socialUrls, setSocialUrls] = useState("");
  const [mode, setMode] = useState("entrevue");
  const [step, setStep] = useState(0);
  const [amorceBusy, setAmorceBusy] = useState(false);
  const [panelKind, setPanelKind] = useState("web");

  useEffect(() => {
    const prefill = inscriptionPrefill(dossier.oqlf_data);
    setValues({ ...prefill, ...(dossier.module1_data || {}) });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dossier.id]);

  const runEnrich = async () => {
    setEnrichBusy(true);
    setPanelKind("web");
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

  const reportAmorce = async () => {
    setAmorceBusy(true);
    try {
      const { data } = await api.get(`/dossiers/${dossier.id}/amorce/proposals`);
      const props = data.proposals || [];
      if (!props.length) {
        toast.info((data.warnings && data.warnings[0]) || "Aucune réponse vocale à reporter");
        return;
      }
      setPanelKind("amorce");
      setProposals(props);
      setEnrichMeta({ site_used: [], warnings: data.warnings || [] });
    } catch (e) {
      toast.error("Report de l'entrevue vocale impossible");
    } finally { setAmorceBusy(false); }
  };

  const runLangProof = async () => {
    setEnrichBusy(true);
    setPanelKind("web");
    try {
      const site = values["s1.sites_web"] || dossier.oqlf_data?.site_web || "";
      const socials = socialUrls.split(/[\n,;\s]+/).map((s) => s.trim()).filter(Boolean);
      const { data } = await api.post(`/dossiers/${dossier.id}/language-proof`, {
        site_url: site, social_urls: socials.length ? socials : undefined,
      });
      const ev = data.evidence || [];
      await Promise.all(ev.map(async (e) => {
        if (e.document_id) {
          try {
            const r = await api.get(`/documents/${e.document_id}/download`, { responseType: "blob" });
            e.thumbUrl = URL.createObjectURL(r.data);
          } catch { e.thumbUrl = null; }
        }
      }));
      setProposals(data.proposals || []);
      setEnrichMeta({ site_used: [], warnings: data.warnings || [], evidence: ev });
      if (!(data.proposals || []).length && !ev.length) toast.info("Aucune preuve générée");
      else toast.success("Preuve linguistique générée et jointe au dossier");
    } catch (e) {
      toast.error("Évaluation de la langue impossible");
    } finally { setEnrichBusy(false); }
  };

  const viewProof = async (docId) => {
    try {
      const resp = await api.get(`/documents/${docId}/download`, { responseType: "blob" });
      window.open(URL.createObjectURL(resp.data), "_blank");
    } catch { toast.error("Capture indisponible"); }
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

  const save = async (silent = false) => {
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
      if (!silent) toast.success("Module 1 enregistré");
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
  const totalSteps = sections.length;
  const inReview = step >= totalSteps;
  const wizSection = inReview ? null : sections[Math.min(step, totalSteps - 1)];
  const overallPct = Math.round(sections.reduce((a, s) => a + sectionCompletion(s), 0) / (sections.length || 1));

  const shouldShowField = (sec, f) => {
    if (!f.showIf) return true;
    return f.showIf.in.includes(values[`${sec.id}.${f.showIf.field}`]);
  };
  const missingFields = [];
  sections.forEach((sec, idx) => {
    sec.fields.forEach((f) => {
      if (f.type === "table") return;
      if (!shouldShowField(sec, f)) return;
      const v = values[`${sec.id}.${f.id}`];
      if (v === undefined || v === "" || (Array.isArray(v) && v.length === 0))
        missingFields.push({ sectionTitre: sec.titre, idx, label: f.label });
    });
  });

  const actionBar = (
    <Card className="p-3 space-y-2 bg-blue-50/60 border-blue-200">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs text-blue-800">
          <Info size={15} />
          {dossier.echeance_module1
            ? <span>Échéance légale : <b>{dossier.echeance_module1}</b> ({dossier.jours_restants_module1} jours) — 3 mois après l'attestation d'inscription.</span>
            : <span>Saisissez la date d'attestation d'inscription pour calculer l'échéance légale.</span>}
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="flex rounded-lg border border-slate-200 overflow-hidden">
            <button onClick={() => setMode("entrevue")} data-testid="m1-mode-entrevue"
              className={`px-3 py-1.5 text-xs font-medium ${mode === "entrevue" ? "bg-[#0F2B48] text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}>Entrevue guidée</button>
            <button onClick={() => setMode("form")} data-testid="m1-mode-form"
              className={`px-3 py-1.5 text-xs font-medium ${mode === "form" ? "bg-[#0F2B48] text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}>Formulaire complet</button>
          </div>
          <Button size="sm" variant="outline" onClick={runEnrich} disabled={enrichBusy} data-testid="module1-enrich-button" className="border-emerald-300 text-emerald-800 hover:bg-emerald-50">
            <Sparkles size={15} className="mr-1" /> {enrichBusy ? "Recherche…" : "Pré-remplir par recherche Web"}
          </Button>
          <Button size="sm" variant="outline" onClick={reportAmorce} disabled={amorceBusy} data-testid="module1-amorce-report" className="border-indigo-300 text-indigo-800 hover:bg-indigo-50">
            <Mic size={15} className="mr-1" /> {amorceBusy ? "Report…" : "Reporter l'entrevue vocale"}
          </Button>
          <Button size="sm" variant="outline" onClick={runLangProof} disabled={enrichBusy} data-testid="module1-langproof-button" className="border-blue-300 text-blue-800 hover:bg-blue-50">
            <Camera size={15} className="mr-1" /> Évaluer la langue + preuve
          </Button>
          <Button size="sm" variant="outline" onClick={exportPdf} data-testid="export-pdf-module1-button">
            <FileDown size={15} className="mr-1" /> Export PDF
          </Button>
          <Button size="sm" onClick={() => save()} disabled={saving} data-testid="module1-save-button" className="bg-[#0F2B48] hover:bg-[#0F2B48]/90">
            <Save size={15} className="mr-1" /> {saving ? "Enregistrement…" : "Enregistrer"}
          </Button>
        </div>
      </div>
      <div className="w-full flex flex-wrap items-center gap-2">
        <label className="text-xs text-slate-600 whitespace-nowrap">URL de médias sociaux à capturer (optionnel) :</label>
        <Input value={socialUrls} onChange={(e) => setSocialUrls(e.target.value)} data-testid="module1-social-urls"
          placeholder="https://linkedin.com/company/…  https://facebook.com/…" className="flex-1 min-w-[220px] h-8 text-xs bg-white" />
      </div>
    </Card>
  );

  return (
    <div className="space-y-4">
      {actionBar}
      {proposals !== null && (
        <WebEnrichPanel proposals={proposals} meta={enrichMeta} onApply={applyProposals} onClose={() => setProposals(null)} onViewProof={viewProof}
          title={panelKind === "amorce" ? "Réponses de l'entrevue vocale (amorce mobile)" : undefined}
          subtitle={panelKind === "amorce" ? "Acceptez ou refusez chaque réponse transcrite et traduite en français. Seuls les champs acceptés seront reportés dans le Module 1." : undefined} />
      )}

      {mode === "entrevue" ? (
        <div className="max-w-3xl mx-auto space-y-4" data-testid="m1-entrevue">
          <Card className="p-3 bg-white">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
              <span>Entrevue guidée — collecte des renseignements auprès du responsable</span>
              <span data-testid="m1-entrevue-progress">{inReview ? "Révision" : `Étape ${step + 1} sur ${totalSteps}`} · {overallPct}% complété</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
              <div className="h-full bg-[#0F2B48] transition-all" style={{ width: `${inReview ? 100 : Math.round(((step + 1) / (totalSteps + 1)) * 100)}%` }} />
            </div>
          </Card>

          {!inReview ? (
            <Card className="p-6" data-testid={`m1-entrevue-section-${wizSection.id}`}>
              <h3 className="font-display text-lg font-bold text-[#0F2B48]" data-testid="m1-entrevue-step-title">{wizSection.titre}</h3>
              <p className="text-xs text-slate-500 mb-5">Répondez aux questions ci‑dessous. Les champs déjà remplis proviennent du pré‑remplissage (recherche Web / preuve) — vérifiez et corrigez au besoin.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {wizSection.fields.map((f) => (
                  <div key={f.id} className={f.type === "table" || f.type === "textarea" ? "md:col-span-2" : ""}>
                    <FieldRenderer field={f} sectionId={wizSection.id} values={values} onChange={onChange} dossierId={dossier.id} />
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between mt-6">
                <Button size="sm" variant="outline" disabled={step === 0} onClick={() => setStep((s) => Math.max(0, s - 1))} data-testid="m1-entrevue-prev">
                  <ChevronLeft size={15} className="mr-1" /> Précédent
                </Button>
                <span className="text-[11px] text-slate-400">{sectionCompletion(wizSection)}% de cette section</span>
                <Button size="sm" onClick={() => { save(true); setStep((s) => s + 1); }} data-testid="m1-entrevue-next" className="bg-[#0F2B48] hover:bg-[#0F2B48]/90">
                  {step === totalSteps - 1 ? "Vers la révision" : "Suivant"} <ChevronRight size={15} className="ml-1" />
                </Button>
              </div>
            </Card>
          ) : (
            <Card className="p-6" data-testid="m1-entrevue-review">
              <h3 className="font-display text-lg font-bold text-[#0F2B48] mb-1">Révision des réponses</h3>
              <p className="text-xs text-slate-500 mb-5">Vérifiez chaque section avant de finaliser. Vous pouvez revenir modifier une réponse.</p>

              {missingFields.length > 0 ? (
                <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50/70 p-4" data-testid="m1-remaining">
                  <p className="text-xs font-semibold text-amber-800 mb-2">
                    <span data-testid="m1-remaining-count">{missingFields.length}</span> question(s) restante(s) à compléter avant la transmission à l'Office
                  </p>
                  <ul className="space-y-1 max-h-56 overflow-auto">
                    {missingFields.map((m, i) => (
                      <li key={i} className="flex items-center justify-between gap-2 text-xs" data-testid={`m1-remaining-item-${i}`}>
                        <span className="text-slate-600"><span className="text-slate-400">{m.sectionTitre} · </span>{m.label}</span>
                        <button onClick={() => setStep(m.idx)} data-testid={`m1-remaining-goto-${i}`}
                          className="shrink-0 rounded-md bg-white border border-amber-300 px-2 py-0.5 text-amber-700 hover:bg-amber-100">Aller</button>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="mb-5 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/70 p-4 text-xs font-semibold text-emerald-700" data-testid="m1-remaining-complete">
                  <CheckCircle2 size={15} /> Toutes les questions sont complétées. Le dossier est prêt à être transmis.
                </div>
              )}

              <div className="space-y-2">
                {sections.map((s, i) => {
                  const pct = sectionCompletion(s);
                  return (
                    <div key={s.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3 text-xs" data-testid={`m1-review-${s.id}`}>
                      <span className="text-slate-700">{s.titre}</span>
                      <div className="flex items-center gap-3">
                        <span className={`font-mono ${pct === 100 ? "text-green-600" : "text-amber-600"}`}>{pct}%</span>
                        <Button size="sm" variant="outline" onClick={() => setStep(i)} data-testid={`m1-review-edit-${s.id}`}>Modifier</Button>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center justify-between mt-6">
                <Button size="sm" variant="outline" onClick={() => setStep(totalSteps - 1)} data-testid="m1-review-back">
                  <ChevronLeft size={15} className="mr-1" /> Revenir
                </Button>
                <Button size="sm" onClick={() => save()} disabled={saving} data-testid="m1-entrevue-finish" className="bg-green-700 hover:bg-green-700/90">
                  <CheckCircle2 size={15} className="mr-1" /> {saving ? "Enregistrement…" : "Terminer et enregistrer"}
                </Button>
              </div>
            </Card>
          )}
        </div>
      ) : (
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
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${isActive ? "bg-[#0F2B48] text-white" : "hover:bg-slate-100 text-slate-600"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="line-clamp-2">{s.titre}</span>
                    <span className={`text-[10px] font-mono ${isActive ? "text-blue-200" : pct === 100 ? "text-green-600" : "text-slate-400"}`}>{pct}%</span>
                  </div>
                </button>
              );
            })}
          </aside>
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
      )}
    </div>
  );
}
