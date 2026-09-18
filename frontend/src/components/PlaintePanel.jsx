import { useEffect, useState } from "react";
import api, { downloadPdf } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import {
  ShieldAlert, MessageSquareWarning, Save, Paperclip, Trash2, MessageSquarePlus,
  Download, FolderOpen, CheckCircle2, ExternalLink, FileDown, Copy, Mail,
} from "lucide-react";

const STATUTS = [
  { value: "a_faire", label: "À faire", cls: "bg-slate-100 text-slate-600" },
  { value: "en_cours", label: "En cours", cls: "bg-blue-100 text-blue-700" },
  { value: "fait", label: "Fait", cls: "bg-emerald-100 text-emerald-700" },
  { value: "sans_objet", label: "Sans objet", cls: "bg-slate-100 text-slate-400" },
];
const RESOLUTIONS = [
  { value: "amiable", label: "Résolue à l'amiable" },
  { value: "classee", label: "Classée (plainte non fondée)" },
  { value: "infirmee", label: "Ordonnance infirmée" },
  { value: "amende", label: "Amende / jugement" },
];

const InspectorAlert = () => (
  <div className="flex items-start gap-3 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-red-800" data-testid="plainte-inspector-alert">
    <ShieldAlert size={20} className="mt-0.5 shrink-0" />
    <div className="text-sm">
      <p className="font-semibold">Un inspecteur se présente ? Exigez sa carte.</p>
      <p className="mt-1">Un inspecteur de l'OQLF doit, sur demande, attester sa qualité et présenter sa carte d'identité — vérifiez-la. Un inspecteur n'est pas un conseiller en francisation. On ne peut rien lui refuser : <b>tout refus est une entrave, passible automatiquement d'une amende.</b></p>
    </div>
  </div>
);

function StageCard({ dossierId, stage, onUpdated }) {
  const [statut, setStatut] = useState(stage.statut);
  const [date, setDate] = useState(stage.date || "");
  const [dateLimite, setDateLimite] = useState(stage.date_limite || "");
  const [note, setNote] = useState(stage.note || "");
  const [echange, setEchange] = useState("");
  const [busy, setBusy] = useState(false);
  const [pieces, setPieces] = useState([]);
  const cat = `plainte:${stage.key}`;
  const stStyle = STATUTS.find((x) => x.value === stage.statut) || STATUTS[0];

  const loadPieces = () => api.get(`/dossiers/${dossierId}/documents`)
    .then(({ data }) => setPieces(data.filter((d) => d.category === cat)))
    .catch(() => {});
  useEffect(() => { loadPieces(); }, [dossierId, stage.key]);

  const save = async (extra = {}) => {
    setBusy(true);
    try {
      const { data } = await api.patch(`/dossiers/${dossierId}/plainte/stage/${stage.key}`, {
        statut, date: date || null, date_limite: dateLimite || null, note, ...extra,
      });
      toast.success("Étape mise à jour");
      setEchange("");
      onUpdated(data);
    } catch (e) { toast.error("Erreur"); }
    finally { setBusy(false); }
  };

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.post(`/dossiers/${dossierId}/documents?category=${encodeURIComponent(cat)}`, fd,
        { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Pièce jointe ajoutée");
      loadPieces();
    } catch (err) { toast.error("Téléversement impossible"); }
    e.target.value = "";
  };

  const removePiece = async (id) => {
    try { await api.delete(`/documents/${id}`); loadPieces(); } catch (e) { toast.error("Erreur"); }
  };

  return (
    <Card className="p-5 space-y-4" data-testid={`plainte-stage-${stage.key}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#0F2B48] text-white text-[11px] font-bold">{stage.ordre}</span>
            <h3 className="font-display font-bold text-[#0F2B48]">{stage.label}</h3>
          </div>
          <p className="text-sm text-slate-500 mt-1.5 max-w-2xl">{stage.description}</p>
        </div>
        <span className={`shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-full ${stStyle.cls}`} data-testid={`plainte-stage-${stage.key}-badge`}>{stStyle.label}</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="space-y-1.5">
          <Label className="text-xs">Statut</Label>
          <Select value={statut} onValueChange={setStatut}>
            <SelectTrigger data-testid={`plainte-stage-${stage.key}-statut`}><SelectValue /></SelectTrigger>
            <SelectContent className="bg-white">
              {STATUTS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Date de l'événement</Label>
          <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} data-testid={`plainte-stage-${stage.key}-date`} />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Échéance</Label>
          <Input type="date" value={dateLimite} onChange={(e) => setDateLimite(e.target.value)} data-testid={`plainte-stage-${stage.key}-echeance`} />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label className="text-xs">Note</Label>
        <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} data-testid={`plainte-stage-${stage.key}-note`} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={() => save()} disabled={busy} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid={`plainte-stage-${stage.key}-save`}>
          <Save size={14} className="mr-1" /> Enregistrer
        </Button>
        <label className="inline-flex items-center gap-1 text-sm text-[#2563EB] cursor-pointer hover:underline" data-testid={`plainte-stage-${stage.key}-upload-label`}>
          <Paperclip size={14} /> Joindre une pièce
          <input type="file" className="hidden" accept=".pdf,.png,.jpg,.jpeg,.webp" onChange={upload} data-testid={`plainte-stage-${stage.key}-upload`} />
        </label>
      </div>

      {pieces.length > 0 && (
        <div className="space-y-1.5">
          {pieces.map((p) => (
            <div key={p.id} className="flex items-center gap-2 text-sm rounded-lg bg-slate-50 border border-slate-100 px-3 py-1.5" data-testid={`plainte-piece-${p.id}`}>
              <FolderOpen size={14} className="text-slate-400" />
              <span className="truncate flex-1 text-slate-700">{p.original_filename}</span>
              <button onClick={() => window.open(`${api.defaults.baseURL}/documents/${p.id}/download`, "_blank")} className="text-slate-400 hover:text-slate-600" title="Télécharger"><Download size={14} /></button>
              <button onClick={() => removePiece(p.id)} className="text-slate-400 hover:text-red-600" title="Supprimer" data-testid={`plainte-piece-${p.id}-delete`}><Trash2 size={14} /></button>
            </div>
          ))}
        </div>
      )}

      <div className="border-t border-slate-100 pt-3">
        <h4 className="text-xs font-semibold text-slate-600 mb-2">Journal des échanges</h4>
        <div className="space-y-1.5 mb-2">
          {(stage.historique || []).length === 0 && <p className="text-xs text-slate-400">Aucun échange consigné.</p>}
          {(stage.historique || []).map((h, i) => (
            <div key={i} className="text-xs bg-slate-50 rounded-lg px-3 py-1.5" data-testid={`plainte-stage-${stage.key}-echange-${i}`}>
              <span className="text-slate-400">{new Date(h.date).toLocaleString("fr-CA")} · {h.auteur}</span>
              <div className="text-slate-700">{h.texte}</div>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <Input value={echange} onChange={(e) => setEchange(e.target.value)} placeholder="Consigner un échange…" data-testid={`plainte-stage-${stage.key}-echange-input`} />
          <Button size="sm" variant="outline" disabled={!echange || busy} onClick={() => save({ echange })} data-testid={`plainte-stage-${stage.key}-echange-add`}>
            <MessageSquarePlus size={15} />
          </Button>
        </div>
      </div>
    </Card>
  );
}

const LETTER_TYPES = [
  { value: "accuse_reception", label: "Accusé de réception" },
  { value: "demande_delai", label: "Demande de délai" },
  { value: "correctif_propose", label: "Correctif proposé" },
];

function LettersCard({ dossierId }) {
  const [type, setType] = useState("accuse_reception");
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);

  const generate = async (t) => {
    setBusy(true);
    try {
      const { data } = await api.get(`/dossiers/${dossierId}/plainte/lettre?type=${t}`);
      setDraft(data);
    } catch (e) { toast.error("Erreur"); }
    finally { setBusy(false); }
  };

  const copyDraft = () => {
    if (!draft) return;
    navigator.clipboard?.writeText(`${draft.subject}\n\n${draft.body}`);
    toast.success("Lettre copiée");
  };

  return (
    <Card className="p-5 space-y-3" data-testid="plainte-letters">
      <div className="flex items-center gap-2">
        <Mail size={18} className="text-indigo-600" />
        <h3 className="font-display font-bold text-[#0F2B48]">Modèles de lettre à l'OQLF</h3>
      </div>
      <p className="text-sm text-slate-500">Générez une réponse pré-remplie, adaptez-la, puis copiez-la.</p>
      <div className="flex flex-wrap gap-2">
        {LETTER_TYPES.map((l) => (
          <Button key={l.value} size="sm" variant={type === l.value ? "default" : "outline"}
            className={type === l.value ? "bg-[#0F2B48] hover:bg-[#0F2B48]/90" : ""}
            onClick={() => { setType(l.value); generate(l.value); }}
            disabled={busy} data-testid={`plainte-letter-${l.value}`}>
            {l.label}
          </Button>
        ))}
      </div>
      {draft && (
        <div className="space-y-2">
          <Input value={draft.subject} onChange={(e) => setDraft({ ...draft, subject: e.target.value })} data-testid="plainte-letter-subject" />
          <Textarea rows={10} value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })} data-testid="plainte-letter-body" className="font-mono text-[13px]" />
          <Button size="sm" variant="outline" onClick={copyDraft} data-testid="plainte-letter-copy">
            <Copy size={14} className="mr-2" /> Copier
          </Button>
        </div>
      )}
    </Card>
  );
}

export const PlaintePanel = ({ dossier, onUpdated }) => {
  const [busy, setBusy] = useState(false);
  const pl = dossier.plainte;

  const openPlainte = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/dossiers/${dossier.id}/plainte`);
      toast.success("Dossier de plainte ouvert");
      onUpdated(data);
    } catch (e) { toast.error("Erreur"); }
    finally { setBusy(false); }
  };

  const patchMeta = async (payload) => {
    try {
      const { data } = await api.patch(`/dossiers/${dossier.id}/plainte`, payload);
      onUpdated(data);
    } catch (e) { toast.error("Erreur"); }
  };

  if (!pl || !pl.ouverte) {
    return (
      <div className="space-y-5" data-testid="plainte-empty">
        <InspectorAlert />
        <Card className="p-6 text-center">
          <MessageSquareWarning size={28} className="mx-auto text-indigo-500 mb-3" />
          <h3 className="font-display text-lg font-bold text-[#0F2B48]">Aucune plainte en cours</h3>
          <p className="text-sm text-slate-500 max-w-xl mx-auto mt-1">
            Une entreprise de moins de 25 employés n'est visée par l'Office qu'en cas de plainte. Ouvrez un
            dossier de suivi si vous recevez une communication de l'OQLF (visite d'inspecteur ou lettre) afin
            de suivre la procédure jusqu'à sa résolution.
          </p>
          <Button onClick={openPlainte} disabled={busy} className="mt-4 bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid="plainte-open-button">
            {busy ? "Ouverture…" : "Ouvrir un dossier de plainte"}
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-5" data-testid="plainte-panel">
      <InspectorAlert />

      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-display font-bold text-[#0F2B48]">Dossier de plainte</h3>
          <Button variant="outline" size="sm" onClick={() => downloadPdf(`/dossiers/${dossier.id}/export/plainte`, `dossier_plainte_${dossier.neq || dossier.id}.pdf`)} data-testid="plainte-export-pdf">
            <FileDown size={14} className="mr-2" /> Dossier PDF
          </Button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <div className="space-y-1.5">
            <Label className="text-xs">Référence OQLF</Label>
            <Input defaultValue={pl.reference_oqlf} placeholder="No de dossier / plainte"
              onBlur={(e) => e.target.value !== (pl.reference_oqlf || "") && patchMeta({ reference_oqlf: e.target.value })}
              data-testid="plainte-reference" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Type de communication initiale</Label>
            <Select value={pl.type_communication || ""} onValueChange={(v) => patchMeta({ type_communication: v })}>
              <SelectTrigger data-testid="plainte-type"><SelectValue placeholder="Choisir…" /></SelectTrigger>
              <SelectContent className="bg-white">
                <SelectItem value="inspection">Visite d'un inspecteur</SelectItem>
                <SelectItem value="lettre">Lettre de l'OQLF</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Résolution</Label>
            <Select value={pl.resolution || ""} onValueChange={(v) => patchMeta({ resolution: v })}>
              <SelectTrigger data-testid="plainte-resolution"><SelectValue placeholder="En cours…" /></SelectTrigger>
              <SelectContent className="bg-white">
                {RESOLUTIONS.map((r) => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
        {pl.resolution && (
          <div className="mt-3 flex items-center gap-2 text-sm text-emerald-700" data-testid="plainte-resolved">
            <CheckCircle2 size={15} /> Dossier marqué : {RESOLUTIONS.find((r) => r.value === pl.resolution)?.label}
            <Button size="sm" variant="ghost" className="ml-2 text-slate-500" onClick={() => patchMeta({ ouverte: false })} data-testid="plainte-close-button">Clore le dossier</Button>
          </div>
        )}
      </Card>

      <div className="space-y-4">
        {pl.stages.map((s) => (
          <StageCard key={s.key} dossierId={dossier.id} stage={s} onUpdated={onUpdated} />
        ))}
      </div>

      <LettersCard dossierId={dossier.id} />
    </div>
  );
};
