import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { RegimeAReq } from "@/components/RegimeAReq";
import { U6Tool } from "@/components/U6Tool";
import {
  ChevronDown, ChevronRight, Save, Paperclip, Trash2, Download, Loader2, ScanSearch, Info, Languages, UploadCloud,
} from "lucide-react";

const STATUTS = [
  { value: "non_evalue", label: "En attente d'échantillon", cls: "bg-slate-100 text-slate-500" },
  { value: "a_valider", label: "Échantillon reçu — à valider", cls: "bg-amber-100 text-amber-700" },
  { value: "conforme", label: "Conforme", cls: "bg-emerald-100 text-emerald-700" },
  { value: "non_conforme", label: "Non conforme", cls: "bg-red-100 text-red-700" },
  { value: "sans_objet", label: "Sans objet", cls: "bg-slate-100 text-slate-400" },
];
const FAIT_OPTS = [
  { v: "oui", label: "Oui" },
  { v: "non", label: "Non" },
  { v: "so", label: "S.O." },
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

function ElementCard({ dossierId, theme, index, saved, findings, questions, onUpdated, onOpenU6 }) {
  const isU6 = theme.id === "U6";
  const [donnees, setDonnees] = useState(saved?.donnees || {});
  const [note, setNote] = useState(saved?.note || "");
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pieces, setPieces] = useState([]);
  const cat = `parcoursA:${theme.id}`;
  const st = STATUTS.find((x) => x.value === (saved?.statut || "non_evalue")) || STATUTS[0];
  const qs = questions || [];

  const loadPieces = () => api.get(`/dossiers/${dossierId}/documents`)
    .then(({ data }) => setPieces(data.filter((d) => d.category === cat))).catch(() => {});
  useEffect(() => { loadPieces(); }, [dossierId, theme.id]);

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.patch(`/dossiers/${dossierId}/parcours-a/element/${theme.id}`, { donnees, note });
      toast.success("Obligation documentée");
      onUpdated(data);
    } catch (e) { toast.error("Erreur"); } finally { setBusy(false); }
  };
  const upload = async (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    try {
      await api.post(`/dossiers/${dossierId}/documents?category=${encodeURIComponent(cat)}`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Échantillon déposé");
      loadPieces();
      // L'échantillon est l'élément central → marque l'obligation « documentée » (jamais un verdict).
      try { const { data } = await api.patch(`/dossiers/${dossierId}/parcours-a/element/${theme.id}`, { donnees: { ...donnees, _echantillon_depose: true } }); onUpdated?.(data); } catch (e2) {}
    } catch (err) { toast.error("Téléversement impossible"); }
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
        {isU6 && (
          <span className={`shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-full ${st.cls}`} data-testid={`parcoursa-status-${theme.id}`}>{st.label}</span>
        )}
      </div>

      {findings && findings.length > 0 && (
        <div className="rounded-lg bg-amber-50 border border-amber-100 px-3 py-2 space-y-1">
          <p className="text-[11px] font-semibold text-amber-700">Détecté par l'analyse :</p>
          {findings.map((f) => <p key={f.finding_id} className="text-xs text-slate-700">• {f.constat}</p>)}
        </div>
      )}

      {isU6 ? (
        <button onClick={onOpenU6} data-testid="parcoursa-open-u6"
          className="w-full flex items-center justify-between gap-2 rounded-lg border-2 border-indigo-200 hover:border-indigo-400 bg-indigo-50/60 px-3 py-2.5 transition-all">
          <span className="flex items-center gap-2 text-sm font-semibold text-[#0F2B48]"><Languages size={16} className="text-indigo-600" /> Ouvrir l'outil d'évaluation (par poste, art. 46/46.1)</span>
          <ChevronRight size={16} className="text-indigo-500" />
        </button>
      ) : (
        <>
          {/* PRIMAIRE — l'échantillon est l'élément central */}
          <div className="rounded-xl border-2 border-dashed border-indigo-300 bg-indigo-50/40 p-4" data-testid={`parcoursa-echantillon-${theme.id}`}>
            <h5 className="font-display font-bold text-[#0F2B48] flex items-center gap-2"><UploadCloud size={17} className="text-indigo-600" /> Échantillon / preuve</h5>
            <p className="text-xs text-slate-500 mt-0.5 mb-3">C'est l'élément central de cette obligation : déposez ce que le client a réellement produit (photo d'une enseigne, PDF d'une facture, d'un contrat, d'un catalogue…).</p>
            <label className="flex flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed border-indigo-300 bg-white/70 hover:border-indigo-500 hover:bg-white cursor-pointer py-6 transition-all">
              <UploadCloud size={26} className="text-indigo-500" />
              <span className="text-sm font-semibold text-[#0F2B48]">Déposer une photo ou un PDF</span>
              <span className="text-[11px] text-slate-400">PNG, JPG, WEBP ou PDF</span>
              <input type="file" className="hidden" accept=".pdf,.png,.jpg,.jpeg,.webp" onChange={upload} data-testid={`parcoursa-upload-${theme.id}`} />
            </label>
            {pieces.length > 0 && (
              <div className="mt-3 space-y-1.5">
                <p className="text-[11px] font-semibold text-emerald-700">{pieces.length} échantillon(s) déposé(s)</p>
                {pieces.map((p) => (
                  <div key={p.id} className="flex items-center gap-2 text-xs rounded-lg bg-white border border-slate-200 px-3 py-1.5" data-testid={`parcoursa-piece-${p.id}`}>
                    <Paperclip size={13} className="text-indigo-500 shrink-0" />
                    <span className="truncate flex-1 text-slate-700">{p.original_filename}</span>
                    <button onClick={() => window.open(`${api.defaults.baseURL}/documents/${p.id}/download`, "_blank")} className="text-slate-400 hover:text-slate-600"><Download size={13} /></button>
                    <button onClick={() => removePiece(p.id)} className="text-slate-400 hover:text-red-600"><Trash2 size={13} /></button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* SECONDAIRE — précisions et statut, subordonnés à l'échantillon */}
          <details className="rounded-lg border border-slate-200 bg-slate-50/60" data-testid={`parcoursa-secondary-${theme.id}`}>
            <summary className="cursor-pointer list-none px-3 py-2 flex items-center justify-between gap-2 text-xs font-medium text-slate-500 hover:text-slate-700">
              <span className="flex items-center gap-1.5"><ChevronRight size={13} /> Précisions et statut <span className="text-slate-400">(secondaire, facultatif)</span></span>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${st.cls}`} data-testid={`parcoursa-status-${theme.id}`}>{st.label}</span>
            </summary>
            <div className="px-3 pb-3 pt-1 space-y-3 border-t border-slate-100">
              {qs.map((q) => (
                <div key={q.id} className="space-y-1.5" data-testid={`parcoursa-q-${theme.id}-${q.id}`}>
                  <Label className="text-xs text-slate-600">{q.label}</Label>
                  {q.type === "fait" ? (
                    <div className="flex gap-1.5">
                      {FAIT_OPTS.map((o) => {
                        const on = donnees[q.id] === o.v;
                        return <button key={o.v} type="button" onClick={() => setDonnees((s) => ({ ...s, [q.id]: o.v }))}
                          data-testid={`parcoursa-q-${theme.id}-${q.id}-${o.v}`}
                          className={`text-xs px-3 py-1 rounded-full border ${on ? "bg-[#0F2B48] text-white border-[#0F2B48]" : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"}`}>{o.label}</button>;
                      })}
                    </div>
                  ) : (
                    <Textarea rows={2} value={donnees[q.id] || ""} onChange={(e) => setDonnees((s) => ({ ...s, [q.id]: e.target.value }))} />
                  )}
                </div>
              ))}
              <div className="space-y-1.5">
                <Label className="text-xs text-slate-600">Précisions / mesures prévues pour être conforme</Label>
                <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Décrivez la situation et, au besoin, les correctifs prévus." data-testid={`parcoursa-note-${theme.id}`} />
              </div>
              <Button size="sm" onClick={save} disabled={busy} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid={`parcoursa-save-${theme.id}`}><Save size={14} className="mr-1" /> Enregistrer les précisions</Button>
            </div>
          </details>

          <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-600">
            {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />} Texte de loi
          </button>
          {open && (
            <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
              <p className="text-[13px] text-slate-600 whitespace-pre-line">{theme.texte_loi || "Texte non disponible."}</p>
              {theme.external_citation && <p className="text-[11px] text-slate-400 mt-2">{theme.external_citation}</p>}
            </div>
          )}
        </>
      )}
    </Card>
  );
}

export const ParcoursAElements = ({ dossier, onUpdated, onGoAnalyse }) => {
  const [themes, setThemes] = useState([]);
  const [plan, setPlan] = useState([]);
  const [questionsMap, setQuestionsMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [u6Open, setU6Open] = useState(false);
  const els = dossier.parcours_a_elements || {};
  const profilDone = !!dossier.parcours_a_profil?.completed;
  const applicable = new Set(dossier.parcours_a_applicable || []);
  const infoOnly = new Set(dossier.parcours_a_info_only || []);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get("/catalogue/themes?regime=A"),
      api.get(`/dossiers/${dossier.id}/plan-correction`),
      api.get("/catalogue/parcours-a/questions"),
    ]).then(([t, p, q]) => { setThemes(t.data); setPlan(p.data); setQuestionsMap(q.data); })
      .catch(() => {}).finally(() => setLoading(false));
  }, [dossier.id]);

  const byTheme = {};
  plan.forEach((f) => { (byTheme[f.theme_id] = byTheme[f.theme_id] || []).push(f); });
  const ordered = [...themes].sort((a, b) => (a.prioritaire_amorce === b.prioritaire_amorce) ? a.ordre - b.ordre : (a.prioritaire_amorce ? -1 : 1));
  const evalues = ordered.filter((t) => applicable.has(t.id));
  const rappels = ordered.filter((t) => infoOnly.has(t.id));

  if (loading) return <div className="flex items-center gap-2 text-slate-400 p-8"><Loader2 className="animate-spin" size={18} /> Chargement…</div>;

  if (u6Open) return <U6Tool dossier={dossier} onBack={() => setU6Open(false)} onUpdated={onUpdated} />;

  return (
    <div className="space-y-4" data-testid="parcoursa-elements">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <p className="text-sm text-slate-500">{dossier.parcours_a_traites}/{dossier.parcours_a_total} éléments applicables documentés. Répondez aux questions et joignez vos preuves — l'outil documente les faits, sans rendre de verdict.</p>
        <Button size="sm" variant="outline" onClick={onGoAnalyse} data-testid="parcoursa-go-analyse"><ScanSearch size={15} className="mr-1" /> Analyser des documents</Button>
      </div>

      {!profilDone && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-amber-800 text-xs flex items-start gap-2" data-testid="parcoursa-profil-hint">
          <Info size={14} className="mt-0.5 shrink-0" /> Renseignez d'abord le <b>Profil / démarrage</b> (NEQ, syndicat, activités, effectifs) pour n'afficher que les obligations qui vous concernent. En attendant, toutes les obligations sont affichées.
        </div>
      )}

      {evalues.map((t, i) => (
        <ElementCard key={t.id} dossierId={dossier.id} theme={t} index={i + 1} saved={els[t.id]} findings={byTheme[t.id]} questions={questionsMap[t.id]} onUpdated={onUpdated} onOpenU6={() => setU6Open(true)} />
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
