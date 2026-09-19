import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { RegimeAReq } from "@/components/RegimeAReq";
import {
  ChevronDown, ChevronRight, Save, Paperclip, Trash2, Download, Loader2, ScanSearch, Info,
} from "lucide-react";

const STATUTS = [
  { value: "non_evalue", label: "Non évalué", cls: "bg-slate-100 text-slate-500" },
  { value: "conforme", label: "Conforme", cls: "bg-emerald-100 text-emerald-700" },
  { value: "a_valider", label: "À valider", cls: "bg-amber-100 text-amber-700" },
  { value: "non_conforme", label: "Non conforme", cls: "bg-red-100 text-red-700" },
  { value: "sans_objet", label: "Sans objet", cls: "bg-slate-100 text-slate-400" },
];

function InfoOnlyCard({ theme, index }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className="p-4 space-y-2 bg-slate-50/70" data-testid={`parcoursa-element-${theme.id}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-400 text-white text-[11px] font-bold">{index}</span>
        <span className="text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded bg-slate-200 text-slate-600">{theme.id}</span>
        <span className="text-[11px] text-slate-500">{theme.article}</span>
        <span className="text-[10px] text-slate-500 border border-slate-300 rounded-full px-2 py-0.5">Rappel — protection après les faits</span>
      </div>
      <h4 className="font-display font-bold text-[#0F2B48] leading-snug">{theme.nom_theme}</h4>
      <p className="text-xs text-slate-500">Cette protection s'applique en cas de situation survenue (représailles, harcèlement). Elle n'exige pas d'évaluation préalable : aucune saisie ni diagnostic n'est requis ici.</p>
      <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700">
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />} Texte de loi
      </button>
      {open && (
        <div className="rounded-lg bg-white border border-slate-100 p-3">
          <p className="text-[13px] text-slate-600 whitespace-pre-line">{theme.texte_loi || "Texte non disponible."}</p>
          {theme.external_citation && <p className="text-[11px] text-slate-400 mt-2">{theme.external_citation}</p>}
        </div>
      )}
    </Card>
  );
}

function ElementCard({ dossierId, theme, index, saved, findings, onUpdated }) {
  const [statut, setStatut] = useState(saved?.statut || "non_evalue");
  const [note, setNote] = useState(saved?.note || "");
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pieces, setPieces] = useState([]);
  const cat = `parcoursA:${theme.id}`;
  const st = STATUTS.find((x) => x.value === statut) || STATUTS[0];

  const loadPieces = () => api.get(`/dossiers/${dossierId}/documents`)
    .then(({ data }) => setPieces(data.filter((d) => d.category === cat))).catch(() => {});
  useEffect(() => { loadPieces(); }, [dossierId, theme.id]);

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.patch(`/dossiers/${dossierId}/parcours-a/element/${theme.id}`, { statut, note });
      toast.success("Élément mis à jour");
      onUpdated(data);
    } catch (e) { toast.error("Erreur"); } finally { setBusy(false); }
  };
  const upload = async (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    try { await api.post(`/dossiers/${dossierId}/documents?category=${encodeURIComponent(cat)}`, fd, { headers: { "Content-Type": "multipart/form-data" } }); toast.success("Preuve ajoutée"); loadPieces(); }
    catch (err) { toast.error("Téléversement impossible"); }
    e.target.value = "";
  };
  const removePiece = async (id) => { try { await api.delete(`/documents/${id}`); loadPieces(); } catch (e) {} };

  return (
    <Card className="p-4 space-y-3" data-testid={`parcoursa-element-${theme.id}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#0F2B48] text-white text-[11px] font-bold">{index}</span>
            <span className="text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">{theme.id}</span>
            <span className="text-[11px] text-slate-500">{theme.article}</span>
          </div>
          <h4 className="font-display font-bold text-[#0F2B48] mt-1 leading-snug">{theme.nom_theme}</h4>
        </div>
        <span className={`shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-full ${st.cls}`} data-testid={`parcoursa-status-${theme.id}`}>{st.label}</span>
      </div>

      {findings && findings.length > 0 && (
        <div className="rounded-lg bg-amber-50 border border-amber-100 px-3 py-2 space-y-1">
          <p className="text-[11px] font-semibold text-amber-700">Détecté par l'analyse :</p>
          {findings.map((f) => <p key={f.finding_id} className="text-xs text-slate-700">• {f.constat}</p>)}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-start">
        <div className="space-y-1.5">
          <Select value={statut} onValueChange={setStatut}>
            <SelectTrigger data-testid={`parcoursa-statut-${theme.id}`}><SelectValue /></SelectTrigger>
            <SelectContent className="bg-white">{STATUTS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="sm:col-span-2">
          <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note / justification" data-testid={`parcoursa-note-${theme.id}`} />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={save} disabled={busy} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid={`parcoursa-save-${theme.id}`}><Save size={14} className="mr-1" /> Enregistrer</Button>
        <label className="inline-flex items-center gap-1 text-sm text-[#2563EB] cursor-pointer hover:underline">
          <Paperclip size={14} /> Preuve
          <input type="file" className="hidden" accept=".pdf,.png,.jpg,.jpeg,.webp" onChange={upload} data-testid={`parcoursa-upload-${theme.id}`} />
        </label>
        <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 ml-auto">
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />} Texte de loi
        </button>
      </div>

      {pieces.length > 0 && (
        <div className="space-y-1">
          {pieces.map((p) => (
            <div key={p.id} className="flex items-center gap-2 text-xs rounded-lg bg-slate-50 border border-slate-100 px-3 py-1.5" data-testid={`parcoursa-piece-${p.id}`}>
              <span className="truncate flex-1 text-slate-700">{p.original_filename}</span>
              <button onClick={() => window.open(`${api.defaults.baseURL}/documents/${p.id}/download`, "_blank")} className="text-slate-400 hover:text-slate-600"><Download size={13} /></button>
              <button onClick={() => removePiece(p.id)} className="text-slate-400 hover:text-red-600"><Trash2 size={13} /></button>
            </div>
          ))}
        </div>
      )}

      {open && (
        <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
          <p className="text-[13px] text-slate-600 whitespace-pre-line">{theme.texte_loi || "Texte non disponible."}</p>
          {theme.external_citation && <p className="text-[11px] text-slate-400 mt-2">{theme.external_citation}</p>}
        </div>
      )}
    </Card>
  );
}

export const ParcoursAElements = ({ dossier, onUpdated, onGoAnalyse }) => {
  const [themes, setThemes] = useState([]);
  const [plan, setPlan] = useState([]);
  const [loading, setLoading] = useState(true);
  const els = dossier.parcours_a_elements || {};
  const profilDone = !!dossier.parcours_a_profil?.completed;
  const applicable = new Set(dossier.parcours_a_applicable || []);
  const infoOnly = new Set(dossier.parcours_a_info_only || []);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.get("/catalogue/themes?regime=A"), api.get(`/dossiers/${dossier.id}/plan-correction`)])
      .then(([t, p]) => { setThemes(t.data); setPlan(p.data); }).catch(() => {}).finally(() => setLoading(false));
  }, [dossier.id]);

  const byTheme = {};
  plan.forEach((f) => { (byTheme[f.theme_id] = byTheme[f.theme_id] || []).push(f); });
  const ordered = [...themes].sort((a, b) => (a.prioritaire_amorce === b.prioritaire_amorce) ? a.ordre - b.ordre : (a.prioritaire_amorce ? -1 : 1));
  const evalues = ordered.filter((t) => applicable.has(t.id));
  const rappels = ordered.filter((t) => infoOnly.has(t.id));

  if (loading) return <div className="flex items-center gap-2 text-slate-400 p-8"><Loader2 className="animate-spin" size={18} /> Chargement…</div>;

  return (
    <div className="space-y-4" data-testid="parcoursa-elements">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <p className="text-sm text-slate-500">{dossier.parcours_a_traites}/{dossier.parcours_a_total} éléments applicables traités. Définissez le statut de chaque obligation et joignez vos preuves.</p>
        <Button size="sm" variant="outline" onClick={onGoAnalyse} data-testid="parcoursa-go-analyse"><ScanSearch size={15} className="mr-1" /> Analyser des documents</Button>
      </div>

      {!profilDone && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-amber-800 text-xs flex items-start gap-2" data-testid="parcoursa-profil-hint">
          <Info size={14} className="mt-0.5 shrink-0" /> Renseignez d'abord le <b>Profil / démarrage</b> (NEQ, syndicat, activités, effectifs) pour n'afficher que les obligations qui vous concernent. En attendant, toutes les obligations sont affichées.
        </div>
      )}

      {evalues.map((t, i) => (
        <ElementCard key={t.id} dossierId={dossier.id} theme={t} index={i + 1} saved={els[t.id]} findings={byTheme[t.id]} onUpdated={onUpdated} />
      ))}

      {rappels.length > 0 && (
        <div className="space-y-3 pt-2">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Rappels légaux (protections après les faits)</p>
          {rappels.map((t, i) => <InfoOnlyCard key={t.id} theme={t} index={evalues.length + i + 1} />)}
        </div>
      )}

      {dossier.req_declaration_requise && (
        <div data-testid="parcoursa-element-REQ">
          <div className="flex items-center gap-2 mb-2 mt-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#0F2B48] text-white text-[11px] font-bold">{evalues.length + rappels.length + 1}</span>
            <h4 className="font-display font-bold text-[#0F2B48]">Déclaration au REQ</h4>
          </div>
          <RegimeAReq dossier={dossier} onSaved={onUpdated} />
        </div>
      )}
    </div>
  );
};
