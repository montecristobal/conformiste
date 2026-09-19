import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import {
  ArrowLeft, Plus, Trash2, Save, FileDown, Sparkles, Loader2, AlertTriangle, ShieldAlert, Briefcase, Paperclip, Download,
} from "lucide-react";

const INTERLOC = [
  { key: "clientele", label: "Clientèle externe" },
  { key: "fournisseurs", label: "Fournisseurs" },
  { key: "collegues_hors_qc", label: "Collègues hors Québec" },
  { key: "autre", label: "Autre" },
];

const newPoste = () => ({
  id: (crypto.randomUUID ? crypto.randomUUID() : String(Date.now())),
  titre: "", nb_postes_vises: "", nb_postes_total: "", langues_exigees: "",
  description_tache: { source: "", cnp_ref: "", tasks: [] },
  section1: { interlocuteurs: [], frequence: "", pct_clientele_non_franco: "", nature_taches: "" },
  section2: { inventaire: "", verification_type: "", details: "" },
  section3: { moyens_texte: "", confirmation_40_1: false },
  section4: { motif_offre: "" },
});

const Warn = ({ children, testid }) => (
  <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-300 px-3 py-2 text-amber-900 text-xs" data-testid={testid}>
    <AlertTriangle size={14} className="mt-0.5 shrink-0" /> <span>{children}</span>
  </div>
);
const SectionTitle = ({ n, children }) => (
  <div className="flex items-center gap-2 pt-1">
    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#0F2B48] text-white text-[11px] font-bold">{n}</span>
    <h4 className="font-display font-bold text-[#0F2B48]">{children}</h4>
  </div>
);

function TaskUploads({ dossierId, posteId }) {
  const cat = `parcoursA:U6:${posteId}:preuve`;
  const [pieces, setPieces] = useState([]);
  const load = () => api.get(`/dossiers/${dossierId}/documents`).then(({ data }) => setPieces(data.filter((d) => d.category === cat))).catch(() => {});
  useEffect(() => { load(); }, [posteId]);
  const upload = async (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    try { await api.post(`/dossiers/${dossierId}/documents?category=${encodeURIComponent(cat)}`, fd, { headers: { "Content-Type": "multipart/form-data" } }); toast.success("Preuve ajoutée"); load(); }
    catch { toast.error("Téléversement impossible"); }
    e.target.value = "";
  };
  const remove = async (id) => { try { await api.delete(`/documents/${id}`); load(); } catch {} };
  return (
    <div className="space-y-1.5">
      <label className="inline-flex items-center gap-1 text-sm text-[#2563EB] cursor-pointer hover:underline">
        <Paperclip size={14} /> Joindre une preuve (correspondance, journal d'appels…)
        <input type="file" className="hidden" accept=".pdf,.png,.jpg,.jpeg,.webp" onChange={upload} data-testid="u6-preuve-upload" />
      </label>
      {pieces.map((p) => (
        <div key={p.id} className="flex items-center gap-2 text-xs rounded-lg bg-slate-50 border border-slate-100 px-3 py-1.5">
          <span className="truncate flex-1 text-slate-700">{p.original_filename}</span>
          <button onClick={() => window.open(`${api.defaults.baseURL}/documents/${p.id}/download`, "_blank")} className="text-slate-400 hover:text-slate-600"><Download size={13} /></button>
          <button onClick={() => remove(p.id)} className="text-slate-400 hover:text-red-600"><Trash2 size={13} /></button>
        </div>
      ))}
    </div>
  );
}

function PosteEditor({ dossierId, poste, library, onChange, onDraftMotif, drafting }) {
  const p = poste;
  const set = (patch) => onChange({ ...p, ...patch });
  const setSec = (k, patch) => onChange({ ...p, [k]: { ...p[k], ...patch } });
  const dt = p.description_tache;
  const setTasks = (tasks) => setSec("description_tache", { tasks });

  const pickLibrary = (code) => {
    const fiche = library.find((m) => m.code_cnp === code);
    if (!fiche) return;
    setSec("description_tache", { source: "library", cnp_ref: code, tasks: fiche.taches.map((t) => ({ texte: t, requires_other_lang: false })) });
  };
  const toggleInterloc = (key) => {
    const cur = p.section1.interlocuteurs || [];
    setSec("section1", { interlocuteurs: cur.includes(key) ? cur.filter((x) => x !== key) : [...cur, key] });
  };
  const noTasks = !(dt.tasks && dt.tasks.length);

  return (
    <div className="space-y-6" data-testid="u6-poste-editor">
      {/* Section 0 */}
      <Card className="p-5 space-y-3">
        <SectionTitle n="0">Identification du poste</SectionTitle>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5 sm:col-span-2"><Label className="text-xs">Titre du poste / catégorie d'emploi</Label>
            <Input value={p.titre} onChange={(e) => set({ titre: e.target.value })} data-testid="u6-titre" /></div>
          <div className="space-y-1.5"><Label className="text-xs">Postes visés par l'exigence</Label>
            <Input type="number" value={p.nb_postes_vises} onChange={(e) => set({ nb_postes_vises: e.target.value })} data-testid="u6-nb-vises" /></div>
          <div className="space-y-1.5"><Label className="text-xs">Nombre total de postes de cette catégorie</Label>
            <Input type="number" value={p.nb_postes_total} onChange={(e) => set({ nb_postes_total: e.target.value })} data-testid="u6-nb-total" /></div>
          <div className="space-y-1.5 sm:col-span-2"><Label className="text-xs">Langue(s) exigée(s) en plus du français</Label>
            <Input value={p.langues_exigees} onChange={(e) => set({ langues_exigees: e.target.value })} placeholder="ex. anglais" data-testid="u6-langues" /></div>
        </div>
      </Card>

      {/* Section 0bis */}
      <Card className="p-5 space-y-3">
        <SectionTitle n="0bis">Description de tâches (prérequis)</SectionTitle>
        <p className="text-xs text-slate-500">Partez d'une fiche-type et adaptez-la, ou saisissez vos propres tâches. Cochez celles qui nécessitent une communication dans une langue autre que le français.</p>
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5 min-w-[240px]">
            <Label className="text-xs">Bibliothèque de fiches-types (CNP)</Label>
            <Select value={dt.cnp_ref || ""} onValueChange={pickLibrary}>
              <SelectTrigger data-testid="u6-library-select"><SelectValue placeholder="Choisir un métier" /></SelectTrigger>
              <SelectContent className="bg-white">
                {library.map((m) => <SelectItem key={m.code_cnp} value={m.code_cnp}>{m.titre}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <Button size="sm" variant="outline" onClick={() => setTasks([...(dt.tasks || []), { texte: "", requires_other_lang: false }])} data-testid="u6-add-task">
            <Plus size={14} className="mr-1" /> Ajouter une tâche
          </Button>
        </div>
        {noTasks && <Warn testid="u6-warn-notasks">Sans description de tâches documentée pour ce poste, votre évaluation des besoins linguistiques risque d'être remise en question par l'Office.</Warn>}
        <div className="space-y-2">
          {(dt.tasks || []).map((t, i) => (
            <div key={i} className="flex items-center gap-2" data-testid={`u6-task-${i}`}>
              <Input value={t.texte} onChange={(e) => { const n = [...dt.tasks]; n[i] = { ...t, texte: e.target.value }; setTasks(n); }} className="flex-1" />
              <label className="inline-flex items-center gap-1 text-[11px] text-slate-600 whitespace-nowrap">
                <input type="checkbox" checked={!!t.requires_other_lang} onChange={(e) => { const n = [...dt.tasks]; n[i] = { ...t, requires_other_lang: e.target.checked }; setTasks(n); }} data-testid={`u6-task-lang-${i}`} /> autre langue
              </label>
              <button onClick={() => setTasks(dt.tasks.filter((_, j) => j !== i))} className="text-slate-400 hover:text-red-600"><Trash2 size={14} /></button>
            </div>
          ))}
        </div>
      </Card>

      {/* Section 1 */}
      <Card className="p-5 space-y-3">
        <SectionTitle n="1">Besoins linguistiques réels (art. 46.1, 1°)</SectionTitle>
        <div className="space-y-1.5">
          <Label className="text-xs">Avec qui ce poste communique-t-il dans une langue autre que le français ?</Label>
          <div className="flex flex-wrap gap-2">
            {INTERLOC.map((o) => {
              const on = (p.section1.interlocuteurs || []).includes(o.key);
              return <button key={o.key} onClick={() => toggleInterloc(o.key)} data-testid={`u6-interloc-${o.key}`}
                className={`text-xs px-2.5 py-1 rounded-full border ${on ? "bg-[#0F2B48] text-white border-[#0F2B48]" : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"}`}>{o.label}</button>;
            })}
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5"><Label className="text-xs">Fréquence de ces communications</Label>
            <Select value={p.section1.frequence || ""} onValueChange={(v) => setSec("section1", { frequence: v })}>
              <SelectTrigger data-testid="u6-frequence"><SelectValue placeholder="Choisir" /></SelectTrigger>
              <SelectContent className="bg-white">
                <SelectItem value="quotidienne">Quotidienne</SelectItem>
                <SelectItem value="hebdomadaire">Hebdomadaire</SelectItem>
                <SelectItem value="occasionnelle">Occasionnelle</SelectItem>
              </SelectContent>
            </Select></div>
          <div className="space-y-1.5"><Label className="text-xs">% d'interlocuteurs ne parlant pas français</Label>
            <Input type="number" min={0} max={100} value={p.section1.pct_clientele_non_franco} onChange={(e) => setSec("section1", { pct_clientele_non_franco: e.target.value })} data-testid="u6-pct" />
            <p className="text-[10px] text-slate-400">Élément d'appréciation à documenter — pas un seuil qui détermine une conclusion.</p></div>
        </div>
        <div className="space-y-1.5"><Label className="text-xs">Nature précise des tâches nécessitant cette connaissance</Label>
          <Textarea rows={2} value={p.section1.nature_taches} onChange={(e) => setSec("section1", { nature_taches: e.target.value })} data-testid="u6-nature" /></div>
        <TaskUploads dossierId={dossierId} posteId={p.id} />
      </Card>

      {/* Section 2 */}
      <Card className="p-5 space-y-3">
        <SectionTitle n="2">Insuffisance des connaissances existantes (art. 46.1, 2°)</SectionTitle>
        <div className="space-y-1.5"><Label className="text-xs">Personnel actuel pouvant occuper ce poste (nombre, niveau connu ou estimé dans l'autre langue)</Label>
          <Textarea rows={2} value={p.section2.inventaire} onChange={(e) => setSec("section2", { inventaire: e.target.value })} data-testid="u6-inventaire" /></div>
        <div className="space-y-1.5"><Label className="text-xs">Cette insuffisance a-t-elle été vérifiée…</Label>
          <Select value={p.section2.verification_type || ""} onValueChange={(v) => setSec("section2", { verification_type: v })}>
            <SelectTrigger data-testid="u6-verif-type"><SelectValue placeholder="Choisir" /></SelectTrigger>
            <SelectContent className="bg-white">
              <SelectItem value="formelle">Formellement (test, entretien)</SelectItem>
              <SelectItem value="informelle">De manière informelle (supposition)</SelectItem>
            </SelectContent>
          </Select></div>
        {p.section2.verification_type && p.section2.verification_type !== "formelle" &&
          <Warn testid="u6-warn-verif">Ce critère de l'art. 46.1 exige de s'être ASSURÉ, pas d'avoir présumé, que les connaissances existantes sont insuffisantes.</Warn>}
        <div className="space-y-1.5"><Label className="text-xs">Détails</Label>
          <Textarea rows={2} value={p.section2.details} onChange={(e) => setSec("section2", { details: e.target.value })} data-testid="u6-verif-details" /></div>
      </Card>

      {/* Section 3 */}
      <Card className="p-5 space-y-3">
        <SectionTitle n="3">Réduction du nombre de postes visés (art. 46.1, 3°)</SectionTitle>
        <div className="space-y-1.5"><Label className="text-xs">Moyens envisagés ou déjà mis en place pour réduire le nombre de postes exigeant cette connaissance</Label>
          <Textarea rows={2} value={p.section3.moyens_texte} onChange={(e) => setSec("section3", { moyens_texte: e.target.value })} data-testid="u6-moyens" /></div>
        <div className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-300 px-3 py-2 text-red-900 text-xs" data-testid="u6-gardefou">
          <ShieldAlert size={16} className="mt-0.5 shrink-0" />
          <span>Garde-fou (art. 40.1) : concentrer les tâches en langue autre sur une personne bilingue déjà en poste peut restreindre son droit de travailler en français. La Charte doit être interprétée de manière à ne jamais supprimer ou restreindre ce droit.</span>
        </div>
        <label className="flex items-start gap-2 text-xs text-slate-700">
          <input type="checkbox" className="mt-0.5" checked={!!p.section3.confirmation_40_1} onChange={(e) => setSec("section3", { confirmation_40_1: e.target.checked })} data-testid="u6-confirm-401" />
          Je confirme que la réduction proposée ne repose pas sur une concentration des tâches en langue autre que le français sur le poste d'une personne bilingue existante, au détriment de son droit de travailler en français.
        </label>
        {!p.section3.confirmation_40_1 && <Warn testid="u6-warn-401">Confirmation non cochée : cet avertissement figurera dans l'export final (l'outil documente, il ne bloque pas).</Warn>}
      </Card>

      {/* Section 4 */}
      <Card className="p-5 space-y-3">
        <SectionTitle n="4">Motif à indiquer dans l'offre d'emploi (art. 46, al. 2)</SectionTitle>
        <p className="text-xs text-slate-500">Formulé à partir des faits documentés ci-dessus. Aucune conclusion de conformité n'est produite.</p>
        <Textarea rows={4} value={p.section4.motif_offre} onChange={(e) => setSec("section4", { motif_offre: e.target.value })} data-testid="u6-motif" />
        <Button size="sm" variant="outline" onClick={() => onDraftMotif(p)} disabled={drafting} data-testid="u6-motif-draft">
          {drafting ? <Loader2 size={14} className="mr-1 animate-spin" /> : <Sparkles size={14} className="mr-1" />} Proposer une rédaction (IA)
        </Button>
      </Card>
    </div>
  );
}

export const U6Tool = ({ dossier, onBack, onUpdated }) => {
  const [postes, setPostes] = useState([]);
  const [library, setLibrary] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [drafting, setDrafting] = useState(false);

  useEffect(() => {
    Promise.all([api.get(`/dossiers/${dossier.id}/parcours-a/u6`), api.get("/catalogue/u6/cnp-library")])
      .then(([u, l]) => { const ps = u.data.postes || []; setPostes(ps); setLibrary(l.data); setSelected(ps[0]?.id || null); })
      .catch(() => {}).finally(() => setLoading(false));
  }, [dossier.id]);

  const addPoste = () => { const np = newPoste(); setPostes((ps) => [...ps, np]); setSelected(np.id); };
  const updatePoste = (up) => setPostes((ps) => ps.map((x) => (x.id === up.id ? up : x)));
  const removePoste = (id) => { setPostes((ps) => ps.filter((x) => x.id !== id)); if (selected === id) setSelected(null); };

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.put(`/dossiers/${dossier.id}/parcours-a/u6`, { postes });
      toast.success("Outil U6 enregistré");
      onUpdated?.(data);
    } catch { toast.error("Erreur lors de l'enregistrement"); } finally { setBusy(false); }
  };
  const draftMotif = async (poste) => {
    setDrafting(true);
    try {
      const { data } = await api.post(`/dossiers/${dossier.id}/parcours-a/u6/motif-draft`, { poste });
      updatePoste({ ...poste, section4: { ...poste.section4, motif_offre: data.draft } });
      toast.success("Proposition de rédaction insérée");
    } catch { toast.error("Rédaction IA indisponible"); } finally { setDrafting(false); }
  };
  const exportPdf = async (id) => {
    try {
      const { data } = await api.get(`/dossiers/${dossier.id}/parcours-a/u6/pdf?poste_id=${id}`, { responseType: "blob" });
      const url = URL.createObjectURL(data); const a = document.createElement("a"); a.href = url; a.download = `demarche_u6_${id}.pdf`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      toast.success("Dossier PDF exporté");
    } catch { toast.error("Enregistrez d'abord le poste, puis réessayez."); }
  };

  const cur = postes.find((x) => x.id === selected);
  if (loading) return <div className="flex items-center gap-2 text-slate-400 p-8"><Loader2 className="animate-spin" size={18} /> Chargement…</div>;

  return (
    <div className="space-y-4" data-testid="u6-tool">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700" data-testid="u6-back">
          <ArrowLeft size={16} /> Retour aux obligations
        </button>
        <Button size="sm" onClick={save} disabled={busy} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid="u6-save">
          {busy ? <Loader2 size={14} className="mr-1 animate-spin" /> : <Save size={14} className="mr-1" />} Enregistrer
        </Button>
      </div>

      <div className="rounded-xl bg-indigo-50 border border-indigo-200 px-4 py-3 text-indigo-800 text-sm">
        Outil d'évaluation de l'exigence d'une autre langue (art. 46 et 46.1). Cet outil <b>documente</b> les faits et les preuves, poste par poste ; il ne produit <b>aucun verdict de conformité</b>.
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {postes.map((pp) => (
          <div key={pp.id} className={`flex items-center gap-1 rounded-lg border px-2 py-1 text-sm ${selected === pp.id ? "border-indigo-400 bg-indigo-50 text-[#0F2B48]" : "border-slate-200 bg-white text-slate-600"}`}>
            <button onClick={() => setSelected(pp.id)} className="flex items-center gap-1" data-testid={`u6-poste-tab-${pp.id}`}><Briefcase size={13} /> {pp.titre || "Poste sans titre"}</button>
            <button onClick={() => removePoste(pp.id)} className="text-slate-400 hover:text-red-600"><Trash2 size={12} /></button>
          </div>
        ))}
        <Button size="sm" variant="outline" onClick={addPoste} data-testid="u6-add-poste"><Plus size={14} className="mr-1" /> Ajouter un poste</Button>
      </div>

      {!cur ? (
        <Card className="p-10 text-center text-slate-500" data-testid="u6-empty">
          <Briefcase className="mx-auto text-slate-300 mb-3" size={36} />
          Ajoutez un poste ou une catégorie d'emploi pour commencer l'évaluation.
        </Card>
      ) : (
        <>
          <PosteEditor dossierId={dossier.id} poste={cur} library={library} onChange={updatePoste} onDraftMotif={draftMotif} drafting={drafting} />
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={save} disabled={busy} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid="u6-save-bottom">
              {busy ? <Loader2 size={14} className="mr-1 animate-spin" /> : <Save size={14} className="mr-1" />} Enregistrer
            </Button>
            <Button size="sm" variant="outline" onClick={() => exportPdf(cur.id)} data-testid="u6-export-pdf"><FileDown size={14} className="mr-1" /> Exporter le dossier PDF</Button>
          </div>
        </>
      )}
    </div>
  );
};
