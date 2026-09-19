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
  ShieldAlert, Plus, Paperclip, Trash2, Download, MessageSquarePlus, CheckSquare, Square,
  AlertTriangle, X,
} from "lucide-react";

const COLUMNS = [
  { key: "reception", label: "Réception & Analyse" },
  { key: "reponse_oqlf", label: "En attente de réponse à l'OQLF" },
  { key: "correctif", label: "Correctif en cours" },
  { key: "validation_preuve", label: "Validation de la preuve" },
  { key: "notification", label: "Notification envoyée à l'OQLF" },
  { key: "ferme", label: "Fermé / Conforme" },
];
const GRAVITES = [{ value: "critique", label: "🔴 Critique" }, { value: "moyen", label: "🟡 Moyen" }];
const VALIDITES = [{ value: "fondee", label: "🔴 Fondée" }, { value: "non_fondee", label: "🟢 Non fondée" }];

function daysUntil(d) {
  if (!d) return null;
  return Math.ceil((new Date(d) - new Date()) / 86400000);
}

function CardTile({ m, onClick }) {
  const j = daysUntil(m.date_echeance);
  const slaCls = j != null && j <= 5 ? "bg-red-50 border-red-300" : j != null && j <= 10 ? "bg-amber-50 border-amber-300" : "bg-white border-slate-200";
  return (
    <button onClick={onClick} data-testid={`kanban-card-${m.id}`}
      className={`w-full text-left rounded-xl border-2 p-3 hover:shadow-md transition-all ${slaCls}`}>
      <div className="flex items-center gap-1.5 mb-1">
        {m.gravite === "critique" && <span className="text-[10px]">🔴</span>}
        {m.gravite === "moyen" && <span className="text-[10px]">🟡</span>}
        {m.incontournable && <AlertTriangle size={12} className="text-red-600" />}
        <span className="text-sm font-semibold text-[#0F2B48] truncate">{m.titre}</span>
      </div>
      {m.no_dossier_oqlf && <p className="text-[10px] font-mono text-slate-400">{m.no_dossier_oqlf}</p>}
      <div className="flex items-center justify-between mt-1.5">
        <span className="text-[11px] text-slate-500 truncate">{m.responsable || "—"}</span>
        {m.date_echeance && (
          <span className={`text-[11px] font-semibold ${j != null && j <= 10 ? "text-red-600" : "text-slate-500"}`}>
            {j != null && j < 0 ? `retard ${Math.abs(j)}j` : `J-${j}`}
          </span>
        )}
      </div>
      {m.validite && <span className="inline-block mt-1 text-[10px]">{m.validite === "fondee" ? "🔴 Fondée" : "🟢 Non fondée"}</span>}
    </button>
  );
}

function CardEditor({ dossierId, mesure, onUpdated, onClose }) {
  const [f, setF] = useState(mesure);
  const [echange, setEchange] = useState("");
  const [chk, setChk] = useState("");
  const [pieces, setPieces] = useState([]);
  const cat = `mesure:${mesure.id}`;
  const set = (k, v) => setF({ ...f, [k]: v });

  const loadPieces = () => api.get(`/dossiers/${dossierId}/documents`)
    .then(({ data }) => setPieces(data.filter((d) => d.category === cat))).catch(() => {});
  useEffect(() => { loadPieces(); }, [mesure.id]);

  const patch = async (extra = {}) => {
    try {
      const { data } = await api.patch(`/dossiers/${dossierId}/mesures/${mesure.id}`, { ...f, ...extra });
      onUpdated(data);
      const fresh = (data.mesures || []).find((x) => x.id === mesure.id);
      if (fresh) setF(fresh);
      setEchange("");
      toast.success("Mesure enregistrée");
    } catch (e) { toast.error("Erreur"); }
  };
  const upload = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    try { await api.post(`/dossiers/${dossierId}/documents?category=${encodeURIComponent(cat)}`, fd, { headers: { "Content-Type": "multipart/form-data" } }); toast.success("Preuve ajoutée"); loadPieces(); }
    catch (err) { toast.error("Téléversement impossible"); }
    e.target.value = "";
  };
  const toggleChk = (i) => { const c = [...(f.checklist || [])]; c[i] = { ...c[i], done: !c[i].done }; setF({ ...f, checklist: c }); patch({ checklist: c }); };
  const addChk = () => { if (!chk) return; const c = [...(f.checklist || []), { label: chk, done: false }]; setChk(""); setF({ ...f, checklist: c }); patch({ checklist: c }); };

  return (
    <Card className="p-5 space-y-4" data-testid="kanban-editor">
      <div className="flex items-start justify-between gap-2">
        <Input value={f.titre} onChange={(e) => set("titre", e.target.value)} className="font-semibold text-[#0F2B48]" data-testid="kanban-editor-titre" />
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700" data-testid="kanban-editor-close"><X size={18} /></button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="space-y-1"><Label className="text-xs">Colonne</Label>
          <Select value={f.statut} onValueChange={(v) => { set("statut", v); patch({ statut: v }); }}>
            <SelectTrigger data-testid="kanban-editor-statut"><SelectValue /></SelectTrigger>
            <SelectContent className="bg-white">{COLUMNS.map((c) => <SelectItem key={c.key} value={c.key}>{c.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="space-y-1"><Label className="text-xs">Plainte fondée ?</Label>
          <Select value={f.validite || ""} onValueChange={(v) => set("validite", v)}>
            <SelectTrigger data-testid="kanban-editor-validite"><SelectValue placeholder="—" /></SelectTrigger>
            <SelectContent className="bg-white">{VALIDITES.map((c) => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="space-y-1"><Label className="text-xs">Gravité</Label>
          <Select value={f.gravite || ""} onValueChange={(v) => set("gravite", v)}>
            <SelectTrigger data-testid="kanban-editor-gravite"><SelectValue placeholder="—" /></SelectTrigger>
            <SelectContent className="bg-white">{GRAVITES.map((c) => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="space-y-1"><Label className="text-xs">N° dossier OQLF</Label><Input value={f.no_dossier_oqlf || ""} onChange={(e) => set("no_dossier_oqlf", e.target.value)} /></div>
        <div className="space-y-1"><Label className="text-xs">Responsable</Label><Input value={f.responsable || ""} onChange={(e) => set("responsable", e.target.value)} data-testid="kanban-editor-responsable" /></div>
        <div className="space-y-1"><Label className="text-xs">Date butoir (OQLF)</Label><Input type="date" value={f.date_echeance || ""} onChange={(e) => set("date_echeance", e.target.value)} data-testid="kanban-editor-echeance" /></div>
      </div>
      <label className="flex items-center gap-2 text-sm text-slate-600">
        <input type="checkbox" checked={!!f.incontournable} onChange={(e) => set("incontournable", e.target.checked)} data-testid="kanban-editor-incontournable" /> Échéance incontournable (délai légal)
      </label>
      <div className="space-y-1"><Label className="text-xs">Moyen / correctif</Label><Textarea rows={2} value={f.moyen || ""} onChange={(e) => set("moyen", e.target.value)} data-testid="kanban-editor-moyen" /></div>
      <Button size="sm" onClick={() => patch()} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid="kanban-editor-save">Enregistrer</Button>

      <div className="border-t border-slate-100 pt-3">
        <h4 className="text-xs font-semibold text-slate-600 mb-2">Checklist des preuves</h4>
        {(f.checklist || []).map((c, i) => (
          <button key={i} onClick={() => toggleChk(i)} className="flex items-center gap-2 text-sm text-slate-700 py-0.5">
            {c.done ? <CheckSquare size={15} className="text-emerald-600" /> : <Square size={15} className="text-slate-400" />} {c.label}
          </button>
        ))}
        <div className="flex gap-2 mt-2">
          <Input value={chk} onChange={(e) => setChk(e.target.value)} placeholder="Ajouter une preuve à fournir…" data-testid="kanban-checklist-input" />
          <Button size="sm" variant="outline" onClick={addChk}><Plus size={15} /></Button>
        </div>
      </div>

      <div className="border-t border-slate-100 pt-3">
        <h4 className="text-xs font-semibold text-slate-600 mb-2">Preuves (documents / photos)</h4>
        {pieces.map((p) => (
          <div key={p.id} className="flex items-center gap-2 text-xs rounded-lg bg-slate-50 border border-slate-100 px-3 py-1.5 mb-1">
            <span className="truncate flex-1 text-slate-700">{p.original_filename}</span>
            <button onClick={() => window.open(`${api.defaults.baseURL}/documents/${p.id}/download`, "_blank")} className="text-slate-400 hover:text-slate-600"><Download size={13} /></button>
          </div>
        ))}
        <label className="inline-flex items-center gap-1 text-sm text-[#2563EB] cursor-pointer hover:underline mt-1">
          <Paperclip size={14} /> Joindre une preuve
          <input type="file" className="hidden" accept=".pdf,.png,.jpg,.jpeg,.webp" onChange={upload} data-testid="kanban-editor-upload" />
        </label>
      </div>

      <div className="border-t border-slate-100 pt-3">
        <h4 className="text-xs font-semibold text-slate-600 mb-2">Journal (traçabilité — non modifiable)</h4>
        {(f.journal || []).map((h, i) => (
          <div key={i} className="text-xs bg-slate-50 rounded-lg px-3 py-1.5 mb-1">
            <span className="text-slate-400">{new Date(h.date).toLocaleString("fr-CA")} · {h.auteur}</span>
            <div className="text-slate-700">{h.texte}</div>
          </div>
        ))}
        <div className="flex gap-2 mt-2">
          <Input value={echange} onChange={(e) => setEchange(e.target.value)} placeholder="Consigner un échange…" data-testid="kanban-echange-input" />
          <Button size="sm" variant="outline" disabled={!echange} onClick={() => patch({ echange })} data-testid="kanban-echange-add"><MessageSquarePlus size={15} /></Button>
        </div>
      </div>
    </Card>
  );
}

export const KanbanBoard = ({ dossier, onUpdated }) => {
  const [selected, setSelected] = useState(null);
  const [newTitre, setNewTitre] = useState("");
  const mesures = (dossier.mesures || []).filter((m) => (m.parcours || "B") === "B");
  const selMesure = mesures.find((m) => m.id === selected);

  const add = async () => {
    if (!newTitre) return;
    try {
      const { data } = await api.post(`/dossiers/${dossier.id}/mesures`, { parcours: "B", titre: newTitre, statut: "reception" });
      setNewTitre(""); onUpdated(data); toast.success("Mesure ajoutée");
    } catch (e) { toast.error("Erreur"); }
  };
  const removeCard = async () => {
    if (!selMesure) return;
    try { const { data } = await api.delete(`/dossiers/${dossier.id}/mesures/${selMesure.id}`); setSelected(null); onUpdated(data); } catch (e) {}
  };

  return (
    <div className="space-y-4" data-testid="kanban-board">
      <div className="flex items-start gap-3 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-red-800">
        <ShieldAlert size={18} className="mt-0.5 shrink-0" />
        <p className="text-sm">Inspecteur OQLF : exigez sa carte d'identité. Tout refus est une entrave, passible d'une amende. Le non‑respect des délais de l'Office expose à des sanctions — surveillez les dates butoirs (rouge à J‑10/J‑5).</p>
      </div>

      <div className="flex gap-2">
        <Input value={newTitre} onChange={(e) => setNewTitre(e.target.value)} placeholder="Nouveau manquement / mesure (ex. Étiquetage produit X)…" data-testid="kanban-new-input" />
        <Button onClick={add} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid="kanban-add"><Plus size={16} className="mr-1" /> Ajouter</Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 items-start">
        {COLUMNS.map((col) => {
          const cards = mesures.filter((m) => (m.statut || "reception") === col.key);
          return (
            <div key={col.key} className="rounded-xl bg-slate-50 border border-slate-200 p-2 min-h-[120px]" data-testid={`kanban-col-${col.key}`}>
              <div className="flex items-center justify-between px-1 mb-2">
                <span className="text-[11px] font-semibold text-slate-600 leading-tight">{col.label}</span>
                <span className="text-[10px] text-slate-400 bg-white rounded-full px-1.5">{cards.length}</span>
              </div>
              <div className="space-y-2">
                {cards.map((m) => <CardTile key={m.id} m={m} onClick={() => setSelected(m.id)} />)}
              </div>
            </div>
          );
        })}
      </div>

      {selMesure && (
        <div className="space-y-2">
          <div className="flex justify-end">
            <Button size="sm" variant="ghost" className="text-red-500 hover:text-red-700" onClick={removeCard} data-testid="kanban-delete"><Trash2 size={14} className="mr-1" /> Supprimer la carte</Button>
          </div>
          <CardEditor dossierId={dossier.id} mesure={selMesure} onUpdated={onUpdated} onClose={() => setSelected(null)} />
        </div>
      )}
    </div>
  );
};
