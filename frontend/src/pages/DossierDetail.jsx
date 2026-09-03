import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { StatusBadge, STATUT_OPTIONS } from "@/components/StatusBadge";
import { PipelineStepper } from "@/components/PipelineStepper";
import { Module1Form } from "@/components/Module1Form";
import { Module2Programme } from "@/components/Module2Programme";
import { AuditLog } from "@/components/AuditLog";
import { toast } from "sonner";
import { ArrowLeft, Send, MessageSquarePlus, Calendar } from "lucide-react";

function StagePanel({ dossier, stageKey, onUpdated }) {
  const stage = dossier.stages.find((s) => s.key === stageKey);
  const [statut, setStatut] = useState(stage.statut);
  const [dateLimite, setDateLimite] = useState(stage.date_limite || "");
  const [note, setNote] = useState(stage.note || "");
  const [echange, setEchange] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setStatut(stage.statut); setDateLimite(stage.date_limite || ""); setNote(stage.note || ""); setEchange("");
  }, [stageKey, dossier.id]);

  const save = async (extra = {}) => {
    setBusy(true);
    try {
      const { data } = await api.patch(`/dossiers/${dossier.id}/stage/${stageKey}`, {
        statut, date_limite: dateLimite || null, note, ...extra,
      });
      toast.success("Étape mise à jour");
      setEchange("");
      onUpdated(data);
    } catch (e) { toast.error("Erreur"); }
    finally { setBusy(false); }
  };

  return (
    <Card className="p-6 space-y-5" data-testid={`stage-panel-${stageKey}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-lg font-bold text-[#0F2B48]">{stage.label}</h3>
          <p className="text-sm text-slate-500 max-w-xl">{stage.description}</p>
        </div>
        <StatusBadge statut={stage.statut} testId={`stage-${stageKey}-badge`} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label className="text-xs">Statut</Label>
          <Select value={statut} onValueChange={setStatut}>
            <SelectTrigger data-testid={`stage-${stageKey}-statut-select`}><SelectValue /></SelectTrigger>
            <SelectContent className="bg-white">
              {STATUT_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs flex items-center gap-1"><Calendar size={13} /> Date limite légale</Label>
          <Input type="date" value={dateLimite} onChange={(e) => setDateLimite(e.target.value)} data-testid={`stage-${stageKey}-date-input`} />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label className="text-xs">Note interne</Label>
        <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} data-testid={`stage-${stageKey}-note`} />
      </div>
      <Button size="sm" onClick={() => save()} disabled={busy} data-testid={`stage-${stageKey}-save`} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90">
        <Send size={15} className="mr-1" /> Enregistrer l'étape
      </Button>

      <div className="border-t border-slate-100 pt-4">
        <h4 className="text-sm font-semibold text-slate-700 mb-2">Historique des échanges avec l'OQLF</h4>
        <div className="space-y-2 mb-3">
          {(stage.historique || []).length === 0 && <p className="text-xs text-slate-400">Aucun échange consigné.</p>}
          {(stage.historique || []).map((h, i) => (
            <div key={i} className="text-xs bg-slate-50 rounded-lg px-3 py-2" data-testid={`stage-${stageKey}-echange-${i}`}>
              <span className="text-slate-400">{new Date(h.date).toLocaleString("fr-CA")} · {h.auteur}</span>
              <div className="text-slate-700">{h.texte}</div>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <Input value={echange} onChange={(e) => setEchange(e.target.value)} placeholder="Ajouter un échange…" data-testid={`stage-${stageKey}-echange-input`} />
          <Button size="sm" variant="outline" disabled={!echange || busy} onClick={() => save({ echange })} data-testid={`stage-${stageKey}-echange-add`}>
            <MessageSquarePlus size={15} />
          </Button>
        </div>
      </div>
    </Card>
  );
}

export default function DossierDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [dossier, setDossier] = useState(null);
  const [themes, setThemes] = useState([]);
  const [activeStage, setActiveStage] = useState("inscription");
  const [tab, setTab] = useState("apercu");

  useEffect(() => {
    api.get(`/dossiers/${id}`).then(({ data }) => setDossier(data)).catch(() => navigate("/dashboard"));
    api.get("/catalogue/themes").then(({ data }) => setThemes(data)).catch(() => {});
  }, [id]);

  if (!dossier) return <Layout><div className="py-20 text-center text-slate-400">Chargement…</div></Layout>;

  return (
    <Layout>
      <button onClick={() => navigate("/dashboard")} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-4" data-testid="back-to-dashboard">
        <ArrowLeft size={16} /> Retour au tableau de bord
      </button>

      <div className="flex flex-wrap items-end justify-between gap-3 mb-5">
        <div>
          <h1 className="font-display text-3xl font-extrabold text-[#0F2B48]">{dossier.nom_entreprise}</h1>
          <p className="text-sm text-slate-500 font-mono">NEQ {dossier.neq || "—"} · {dossier.nb_employes_quebec} employés · {dossier.nb_etablissements} établissement(s)</p>
        </div>
        {dossier.echeance_module1 && (
          <div className={`text-sm px-4 py-2 rounded-xl border ${dossier.urgence_module1 === "critical" ? "bg-red-100 text-red-800 border-red-300" : dossier.urgence_module1 === "approaching" ? "bg-amber-100 text-amber-900 border-amber-300" : "bg-slate-100 text-slate-700 border-slate-200"}`}>
            Analyse linguistique due le <b>{dossier.echeance_module1}</b> ({dossier.jours_restants_module1} jours)
          </div>
        )}
      </div>

      <Card className="p-4 mb-6">
        <PipelineStepper stages={dossier.stages} activeKey={activeStage} onSelect={(k) => { setActiveStage(k); setTab("apercu"); }} />
      </Card>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="apercu" data-testid="tab-apercu">Étape & aperçu</TabsTrigger>
          <TabsTrigger value="module1" data-testid="tab-module1">Module 1 — Analyse</TabsTrigger>
          <TabsTrigger value="module2" data-testid="tab-module2">Module 2 — Programme</TabsTrigger>
          <TabsTrigger value="journal" data-testid="tab-journal">Journal d'audit</TabsTrigger>
        </TabsList>

        <TabsContent value="apercu">
          <StagePanel dossier={dossier} stageKey={activeStage} onUpdated={setDossier} />
        </TabsContent>
        <TabsContent value="module1">
          <Module1Form dossier={dossier} onSaved={setDossier} />
        </TabsContent>
        <TabsContent value="module2">
          <Module2Programme dossier={dossier} themes={themes} onSaved={setDossier} />
        </TabsContent>
        <TabsContent value="journal">
          <AuditLog dossierId={dossier.id} />
        </TabsContent>
      </Tabs>
    </Layout>
  );
}
