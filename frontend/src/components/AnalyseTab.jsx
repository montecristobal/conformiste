import { useEffect, useState, useCallback } from "react";
import api, { downloadPdf, openDocument } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import {
  Upload, Link2, FileText, Image as ImageIcon, Globe, Sparkles, Loader2, Eye,
  AlertTriangle, ArrowRightCircle, Mail, Copy, FileDown, CheckCircle2, ShieldQuestion, Trash2,
} from "lucide-react";

function FindingStatus({ statut }) {
  if (statut === "non_conforme")
    return <Badge variant="outline" className="bg-red-100 text-red-800 border-red-300"><AlertTriangle size={12} className="mr-1" /> Non conforme</Badge>;
  return <Badge variant="outline" className="bg-amber-100 text-amber-800 border-amber-300"><ShieldQuestion size={12} className="mr-1" /> À valider par un professionnel</Badge>;
}

function kindIcon(kind) {
  if (kind === "image") return ImageIcon;
  if (kind === "url") return Globe;
  return FileText;
}

function BlobThumb({ docId }) {
  const [src, setSrc] = useState(null);
  useEffect(() => {
    let url;
    api.get(`/documents/${docId}/download`, { responseType: "blob" })
      .then(({ data }) => { url = URL.createObjectURL(data); setSrc(url); })
      .catch(() => {});
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [docId]);
  return src
    ? <img src={src} alt="" className="h-9 w-9 rounded-lg object-cover border border-slate-200 shrink-0" data-testid={`document-thumb-${docId}`} />
    : <div className="h-9 w-9 rounded-lg bg-slate-100 flex items-center justify-center shrink-0"><ImageIcon size={18} className="text-slate-400" /></div>;
}

function DocumentRow({ doc, onAnalyze, analyzing, onDelete, failed }) {
  const Icon = kindIcon(doc.kind);
  const ana = doc.analysis;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4" data-testid={`document-row-${doc.id}`}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3 min-w-0">
          {doc.kind === "image"
            ? <BlobThumb docId={doc.id} />
            : <div className="h-9 w-9 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center shrink-0"><Icon size={18} /></div>}
          <div className="min-w-0">
            <div className="text-sm font-medium text-slate-800 truncate max-w-[360px]">{doc.original_filename}</div>
            <div className="text-[11px] text-slate-400">{new Date(doc.created_at).toLocaleString("fr-CA")}{ana ? ` · ${ana.elements?.length || 0} élément(s)` : ""}</div>
          </div>
          {failed && <Badge variant="outline" className="bg-red-100 text-red-700 border-red-300" data-testid={`document-failed-${doc.id}`}><AlertTriangle size={12} className="mr-1" /> Échec de l'analyse</Badge>}
        </div>
        <div className="flex items-center gap-2">
          {doc.type === "file" && (
            <Button size="sm" variant="ghost" onClick={() => openDocument(doc.id)} data-testid={`document-view-${doc.id}`}>
              <Eye size={15} className="mr-1" /> Voir
            </Button>
          )}
          <Button size="sm" onClick={() => onAnalyze(doc)} disabled={analyzing}
            data-testid={`document-analyze-${doc.id}`} className="bg-[#2563EB] hover:bg-[#2563EB]/90">
            {analyzing ? <Loader2 size={15} className="mr-1 animate-spin" /> : <Sparkles size={15} className="mr-1" />}
            {ana ? "Ré-analyser" : "Analyser"}
          </Button>
          <Button size="sm" variant="ghost" className="text-red-500 hover:text-red-600" onClick={() => onDelete(doc)} data-testid={`document-delete-${doc.id}`}>
            <Trash2 size={15} />
          </Button>
        </div>
      </div>
      {ana && (
        <div className="mt-3 border-t border-slate-100 pt-3 space-y-2">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="font-medium">Langue détectée :</span>
            <Badge variant="outline" className="capitalize">{ana.langue_detectee}</Badge>
            <span className="italic">{ana.resume}</span>
          </div>
          {(ana.elements || []).length === 0 && <p className="text-xs text-slate-400">Aucun élément détecté.</p>}
          {(ana.elements || []).map((el) => (
            <div key={el.id} className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2" data-testid={`finding-${el.id}`}>
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <span className="text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded bg-[#0F2B48] text-white">{el.theme_id}</span>
                <FindingStatus statut={el.statut} />
              </div>
              <p className="text-sm text-slate-700 mt-1">{el.constat}</p>
              {el.mesure_suggeree && <p className="text-xs text-slate-600 mt-1"><b>Mesure suggérée :</b> {el.mesure_suggeree}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function AnalyseTab({ dossier, onMesureAdded }) {
  const dossierId = dossier.id;
  const [documents, setDocuments] = useState([]);
  const [plan, setPlan] = useState([]);
  const [url, setUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const [analyzingId, setAnalyzingId] = useState(null);
  const [convertingId, setConvertingId] = useState(null);
  const [emailModule, setEmailModule] = useState("1");
  const [draft, setDraft] = useState(null);
  const [emailTo, setEmailTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [failedIds, setFailedIds] = useState({});

  const load = useCallback(async () => {
    setLoadError(false);
    try {
      const [d, p] = await Promise.all([
        api.get(`/dossiers/${dossierId}/documents`),
        api.get(`/dossiers/${dossierId}/plan-correction`),
      ]);
      setDocuments(d.data);
      setPlan(p.data);
    } catch (err) {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [dossierId]);

  useEffect(() => { load(); }, [load]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await api.post(`/dossiers/${dossierId}/documents`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Document téléversé");
      await load();
    } catch (err) { toast.error("Échec du téléversement"); }
    finally { setUploading(false); e.target.value = ""; }
  };

  const addUrl = async () => {
    if (!url.trim()) return;
    try {
      await api.post(`/dossiers/${dossierId}/documents/url`, { url: url.trim() });
      setUrl("");
      toast.success("URL ajoutée");
      await load();
    } catch (err) { toast.error("Erreur"); }
  };

  const analyze = async (doc) => {
    setAnalyzingId(doc.id);
    try {
      await api.post(`/documents/${doc.id}/analyze`);
      setFailedIds((p) => { const n = { ...p }; delete n[doc.id]; return n; });
      toast.success("Analyse terminée");
      await load();
    } catch (err) {
      setFailedIds((p) => ({ ...p, [doc.id]: true }));
      toast.error(err.response?.data?.detail || "Erreur d'analyse");
    } finally { setAnalyzingId(null); }
  };

  const removeDoc = async (doc) => {
    if (!window.confirm(`Supprimer « ${doc.original_filename} » et son analyse ?`)) return;
    try {
      await api.delete(`/documents/${doc.id}`);
      toast.success("Document supprimé");
      await load();
    } catch (err) { toast.error("Erreur de suppression"); }
  };

  const convert = async (item) => {
    setConvertingId(item.finding_id);
    try {
      await api.post(`/dossiers/${dossierId}/plan-correction/${item.finding_id}/to-mesure`);
      toast.success("Converti en mesure du Module 2");
      await load();
      onMesureAdded?.();
    } catch (err) { toast.error("Erreur de conversion"); }
    finally { setConvertingId(null); }
  };

  const genDraft = async () => {
    const { data } = await api.get(`/dossiers/${dossierId}/courriel?module=${emailModule}`);
    setDraft(data);
    setEmailTo(data.to || "");
  };

  const copy = (text, label) => { navigator.clipboard.writeText(text); toast.success(`${label} copié`); };
  const mailto = draft ? `mailto:${encodeURIComponent(emailTo)}?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(draft.body)}` : "#";

  return (
    <div className="space-y-6">
      {/* Réception */}
      <Card className="p-5">
        <h3 className="font-display text-lg font-bold text-[#0F2B48] mb-1">Réception de documents</h3>
        <p className="text-sm text-slate-500 mb-4">Téléversez un PDF ou une photo, ou fournissez l'URL d'un site web à analyser.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-6 cursor-pointer hover:border-blue-400 transition-colors" data-testid="upload-dropzone">
            <Upload size={22} className="text-slate-400" />
            <span className="text-sm text-slate-600">{uploading ? "Téléversement…" : "Choisir un fichier (PDF, JPEG, PNG)"}</span>
            <input type="file" accept=".pdf,image/png,image/jpeg,image/webp" className="hidden" onChange={handleUpload} disabled={uploading} data-testid="upload-file-input" />
          </label>
          <div className="flex flex-col justify-center gap-2">
            <Label className="text-xs flex items-center gap-1"><Link2 size={13} /> URL d'un site web</Label>
            <div className="flex gap-2">
              <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://exemple.com" data-testid="url-input" />
              <Button onClick={addUrl} variant="outline" data-testid="add-url-button">Ajouter</Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Documents */}
      <div>
        <h3 className="font-display text-lg font-bold text-[#0F2B48] mb-3">Documents & analyses</h3>
        {loadError ? (
          <Card className="p-8 text-center" data-testid="documents-load-error">
            <p className="text-sm text-red-600 mb-3">Impossible de charger les documents et le plan.</p>
            <Button variant="outline" size="sm" onClick={load} data-testid="retry-load-button">Réessayer</Button>
          </Card>
        ) : loading ? (
          <Card className="p-8 text-center text-sm text-slate-400" data-testid="documents-loading"><Loader2 size={18} className="inline animate-spin mr-2" />Chargement…</Card>
        ) : documents.length === 0 ? (
          <Card className="p-8 text-center text-sm text-slate-400" data-testid="documents-empty">Aucun document. Téléversez un fichier ou ajoutez une URL ci-dessus.</Card>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <DocumentRow key={doc.id} doc={doc} onAnalyze={analyze} analyzing={analyzingId === doc.id} onDelete={removeDoc} failed={!!failedIds[doc.id]} />
            ))}
          </div>
        )}
      </div>

      {/* Plan de correction */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <h3 className="font-display text-lg font-bold text-[#0F2B48]">Plan de correction</h3>
          <Badge variant="outline">{plan.length} élément(s)</Badge>
        </div>
        {plan.length === 0 ? (
          <Card className="p-8 text-center text-sm text-slate-400" data-testid="plan-empty">Analysez au moins un document pour générer le plan de correction.</Card>
        ) : (
          <Card className="p-2" data-testid="plan-correction">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b border-slate-100">
                    <th className="px-3 py-2">Thème</th>
                    <th className="px-3 py-2">Constat</th>
                    <th className="px-3 py-2">Statut</th>
                    <th className="px-3 py-2">Mesure suggérée</th>
                    <th className="px-3 py-2">Échéance</th>
                    <th className="px-3 py-2">Coût</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {plan.map((item) => (
                    <tr key={item.finding_id} className="border-b border-slate-50 align-top" data-testid={`plan-item-${item.finding_id}`}>
                      <td className="px-3 py-2"><span className="text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">{item.theme_id}</span><div className="text-[11px] text-slate-500 mt-1 max-w-[130px]">{item.theme_nom}</div></td>
                      <td className="px-3 py-2 max-w-[220px]"><div className="text-slate-700">{item.constat}</div><div className="text-[10px] text-slate-400 mt-1 truncate">Source : {item.source}</div></td>
                      <td className="px-3 py-2"><FindingStatus statut={item.statut} /></td>
                      <td className="px-3 py-2 max-w-[200px] text-slate-600">{item.mesure_suggeree || "—"}</td>
                      <td className="px-3 py-2 text-slate-600 whitespace-nowrap">{item.echeance_suggeree || "—"}</td>
                      <td className="px-3 py-2 text-slate-600 whitespace-nowrap">{item.cout_approximatif || "—"}</td>
                      <td className="px-3 py-2">
                        {item.converti ? (
                          <span className="text-xs text-green-600 flex items-center gap-1"><CheckCircle2 size={14} /> Converti</span>
                        ) : (
                          <Button size="sm" variant="outline" onClick={() => convert(item)} disabled={convertingId === item.finding_id} data-testid={`convert-${item.finding_id}`}>
                            {convertingId === item.finding_id ? <Loader2 size={14} className="mr-1 animate-spin" /> : <ArrowRightCircle size={14} className="mr-1" />} En mesure
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>

      {/* Courriel */}
      <Card className="p-5">
        <h3 className="font-display text-lg font-bold text-[#0F2B48] mb-1 flex items-center gap-2"><Mail size={18} /> Courriel préparé pour l'OQLF</h3>
        <p className="text-sm text-slate-500 mb-4">Brouillon à réviser et à envoyer vous-même. Le logiciel n'envoie jamais le courriel automatiquement. Le PDF se télécharge séparément (à joindre manuellement).</p>
        <div className="flex items-center gap-2 mb-4">
          <Select value={emailModule} onValueChange={setEmailModule}>
            <SelectTrigger className="w-64" data-testid="email-module-select"><SelectValue /></SelectTrigger>
            <SelectContent className="bg-white">
              <SelectItem value="1">Module 1 — Analyse linguistique</SelectItem>
              <SelectItem value="2">Module 2 — Programme de francisation</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={genDraft} data-testid="generate-draft-button" className="bg-[#0F2B48] hover:bg-[#0F2B48]/90">Générer le brouillon</Button>
        </div>
        {draft && (
          <div className="space-y-3" data-testid="email-draft">
            <div className="space-y-1.5">
              <Label className="text-xs">Destinataire (à saisir)</Label>
              <Input value={emailTo} onChange={(e) => setEmailTo(e.target.value)} placeholder="adresse@oqlf.gouv.qc.ca" data-testid="email-to-input" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Objet</Label>
              <div className="flex gap-2">
                <Input value={draft.subject} readOnly data-testid="email-subject" />
                <Button variant="outline" size="icon" onClick={() => copy(draft.subject, "Objet")}><Copy size={15} /></Button>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Corps du message</Label>
              <Textarea value={draft.body} readOnly rows={8} data-testid="email-body" />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => copy(draft.body, "Message")} data-testid="copy-body-button"><Copy size={15} className="mr-1" /> Copier le message</Button>
              <Button variant="outline" onClick={() => downloadPdf(draft.pdf_path, draft.pdf_filename)} data-testid="download-pdf-button"><FileDown size={15} className="mr-1" /> Télécharger le PDF</Button>
              <a href={mailto} data-testid="mailto-link">
                <Button className="bg-[#2563EB] hover:bg-[#2563EB]/90"><Mail size={15} className="mr-1" /> Ouvrir dans ma messagerie</Button>
              </a>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
