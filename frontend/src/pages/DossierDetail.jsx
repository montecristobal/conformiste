import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
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
import { AnalyseTab } from "@/components/AnalyseTab";
import { AuditLog } from "@/components/AuditLog";
import { OqlfInscriptionForm } from "@/components/OqlfInscriptionForm";
import { AmorcePanel } from "@/components/AmorcePanel";
import { DiagnosticPanel } from "@/components/DiagnosticPanel";
import { RegimeAConformite } from "@/components/RegimeAConformite";
import { ParcoursAStepper } from "@/components/ParcoursAStepper";
import { RegimeAReq } from "@/components/RegimeAReq";
import { toast } from "sonner";
import { ArrowLeft, Send, MessageSquarePlus, Calendar, FileDown } from "lucide-react";


function StagePanel({ dossier, stageKey, onUpdated, onDirtyChange }) {
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

      {stageKey === "inscription" && <OqlfInscriptionForm dossier={dossier} onUpdated={onUpdated} onDirtyChange={onDirtyChange} />}

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
  const { user } = useAuth();
  const isSolo = user?.account_type === "SOLO";
  const [dossier, setDossier] = useState(null);
  const [themes, setThemes] = useState([]);
  const [activeStage, setActiveStage] = useState("inscription");
  const [tab, setTab] = useState("");
  const dirtyRef = useRef(false);

  const confirmLeave = () => {
    if (!dirtyRef.current) return true;
    const ok = window.confirm("Vous avez des modifications non enregistrées dans le formulaire d'inscription. Quitter sans enregistrer ?");
    if (ok) dirtyRef.current = false;
    return ok;
  };

  useEffect(() => {
    api.get(`/dossiers/${id}`).then(({ data }) => setDossier(data)).catch(() => navigate("/dashboard"));
    api.get("/catalogue/themes").then(({ data }) => setThemes(data)).catch(() => {});
  }, [id]);

  const reload = () => api.get(`/dossiers/${id}`).then(({ data }) => setDossier(data)).catch(() => {});

  if (!dossier) return <Layout><div className="py-20 text-center text-slate-400">Chargement…</div></Layout>;

  const isRegimeA = dossier.regime === "A";
  const defaultTab = isRegimeA ? "conformite" : "diagnostic";
  const visibleStages = (dossier.stages || []).filter((s) => s.key !== "comite" || dossier.comite_requis);

  return (
    <Layout>
      {!isSolo && (
        <button onClick={() => { if (confirmLeave()) navigate("/dashboard"); }} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-4" data-testid="back-to-dashboard">
          <ArrowLeft size={16} /> Retour au tableau de bord
        </button>
      )}

      <div className="flex flex-wrap items-end justify-between gap-3 mb-5">
        <div>
          <h1 className="font-display text-3xl font-extrabold text-[#0F2B48]">{dossier.nom_entreprise}</h1>
          <p className="text-sm text-slate-500 font-mono">NEQ {dossier.neq || "—"} · {dossier.nb_employes_quebec} employés · {dossier.nb_etablissements} établissement(s)</p>
        </div>
        {isRegimeA ? (
          <div className="flex flex-col items-end gap-2">
            <div className="text-sm px-4 py-2 rounded-xl border bg-indigo-50 text-indigo-800 border-indigo-200" data-testid="regime-a-badge">
              Parcours PME · {dossier.nb_employes_quebec} employé(s) au Québec
            </div>
            {dossier.req_declaration_requise && (
              <div className="text-xs px-3 py-1.5 rounded-lg border bg-white text-indigo-700 border-indigo-200" data-testid="regime-a-req-badge">
                Déclaration REQ {dossier.req_declaration ? "enregistrée" : "requise"}
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-end gap-2">
            <div className={`text-sm px-4 py-2 rounded-xl border ${dossier.comite_requis ? "bg-indigo-50 text-indigo-800 border-indigo-200" : "bg-slate-100 text-slate-600 border-slate-200"}`} data-testid="regime-b-comite-badge">
              {dossier.comite_requis
                ? "Comité de francisation requis · 100 employés et plus"
                : "Sans comité de francisation · 25 à 99 employés"}
            </div>
            {dossier.echeance_module1 && (
              <div className={`text-sm px-4 py-2 rounded-xl border ${dossier.urgence_module1 === "critical" ? "bg-red-100 text-red-800 border-red-300" : dossier.urgence_module1 === "approaching" ? "bg-amber-100 text-amber-900 border-amber-300" : "bg-slate-100 text-slate-700 border-slate-200"}`}>
                Analyse linguistique due le <b>{dossier.echeance_module1}</b> ({dossier.jours_restants_module1} jours)
              </div>
            )}
          </div>
        )}
      </div>

      {isRegimeA ? (
        <Card className="p-4 mb-6">
          <ParcoursAStepper dossier={dossier} active={tab || defaultTab} onSelect={(k) => setTab(k)} />
        </Card>
      ) : (
        <Card className="p-4 mb-6">
          <PipelineStepper stages={visibleStages} activeKey={activeStage} onSelect={(k) => { if (confirmLeave()) { setActiveStage(k); setTab("apercu"); } }} />
        </Card>
      )}

      <Tabs value={tab || defaultTab} onValueChange={(v) => { if (confirmLeave()) setTab(v); }}>
        <TabsList className="mb-4">
          {isRegimeA ? (
            <>
              <TabsTrigger value="conformite" data-testid="tab-conformite">Obligations universelles</TabsTrigger>
              <TabsTrigger value="req" data-testid="tab-req">Déclaration REQ</TabsTrigger>
              <TabsTrigger value="amorce" data-testid="tab-amorce">Amorce (mobile)</TabsTrigger>
              <TabsTrigger value="analyse" data-testid="tab-analyse">Analyse & non-conformités</TabsTrigger>
              <TabsTrigger value="journal" data-testid="tab-journal">Journal d'audit</TabsTrigger>
              <TabsTrigger value="plainte" data-testid="tab-plainte" disabled>Plainte (à venir)</TabsTrigger>
            </>
          ) : (
            <>
              <TabsTrigger value="diagnostic" data-testid="tab-diagnostic">Aperçu du diagnostic</TabsTrigger>
              <TabsTrigger value="apercu" data-testid="tab-apercu">Étape & aperçu</TabsTrigger>
              <TabsTrigger value="amorce" data-testid="tab-amorce">Amorce (mobile)</TabsTrigger>
              <TabsTrigger value="module1" data-testid="tab-module1">Module 1 — Analyse</TabsTrigger>
              <TabsTrigger value="module2" data-testid="tab-module2">Module 2 — Programme</TabsTrigger>
              <TabsTrigger value="analyse" data-testid="tab-analyse">Analyse & non-conformités</TabsTrigger>
              <TabsTrigger value="journal" data-testid="tab-journal">Journal d'audit</TabsTrigger>
            </>
          )}
        </TabsList>

        {isRegimeA ? (
          <>
            <TabsContent value="conformite">
              <RegimeAConformite dossier={dossier} onGoAnalyse={() => setTab("analyse")} />
            </TabsContent>
            <TabsContent value="req">
              <RegimeAReq dossier={dossier} onSaved={setDossier} />
            </TabsContent>
            <TabsContent value="amorce">
              <AmorcePanel dossier={dossier} />
            </TabsContent>
            <TabsContent value="analyse">
              <AnalyseTab dossier={dossier} onMesureAdded={reload} />
            </TabsContent>
            <TabsContent value="journal">
              <AuditLog dossierId={dossier.id} />
            </TabsContent>
          </>
        ) : (
          <>
            <TabsContent value="diagnostic">
              <DiagnosticPanel dossier={dossier} onComplete={() => { if (confirmLeave()) setTab("module1"); }} />
            </TabsContent>
            <TabsContent value="apercu">
              <StagePanel dossier={dossier} stageKey={activeStage} onUpdated={setDossier} onDirtyChange={(b) => { dirtyRef.current = b; }} />
            </TabsContent>
            <TabsContent value="amorce">
              <AmorcePanel dossier={dossier} />
            </TabsContent>
            <TabsContent value="module1">
              <Module1Form dossier={dossier} onSaved={setDossier} />
            </TabsContent>
            <TabsContent value="module2">
              <Module2Programme dossier={dossier} themes={themes} onSaved={setDossier} />
            </TabsContent>
            <TabsContent value="analyse">
              <AnalyseTab dossier={dossier} onMesureAdded={reload} />
            </TabsContent>
            <TabsContent value="journal">
              <AuditLog dossierId={dossier.id} />
            </TabsContent>
          </>
        )}
      </Tabs>
    </Layout>
  );
}
