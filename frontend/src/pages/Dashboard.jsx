import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Layout } from "@/components/Layout";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "@/components/StatusBadge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Plus, FolderOpen, AlarmClock, Building2, Layers } from "lucide-react";

function urgencyCls(u) {
  if (u === "critical") return "bg-red-100 text-red-800 border-red-300 animate-pulse";
  if (u === "approaching") return "bg-amber-100 text-amber-900 border-amber-300";
  return "bg-slate-100 text-slate-700 border-slate-200";
}

function CreateDossierDialog({ clients, isPro, onCreated }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ nom_entreprise: "", neq: "", nb_employes_quebec: 0, nb_etablissements: 1, date_attestation_inscription: "", client_id: "" });
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      const payload = { ...form,
        nb_employes_quebec: Number(form.nb_employes_quebec) || 0,
        nb_etablissements: Number(form.nb_etablissements) || 1,
        client_id: isPro ? (form.client_id || null) : null,
        date_attestation_inscription: form.date_attestation_inscription || null };
      const { data } = await api.post("/dossiers", payload);
      toast.success("Dossier créé");
      setOpen(false);
      onCreated(data);
    } catch (e) { toast.error("Erreur lors de la création"); }
    finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button data-testid="create-dossier-button" className="bg-[#0F2B48] hover:bg-[#0F2B48]/90">
          <Plus size={17} className="mr-1" /> Nouveau dossier
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-white">
        <DialogHeader><DialogTitle>Nouveau dossier de francisation</DialogTitle>
          <DialogDescription>Renseignez l'entreprise et la date d'attestation pour calculer l'échéance légale.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          {isPro && (
            <div className="space-y-1.5">
              <Label>Client</Label>
              <Select value={form.client_id} onValueChange={(v) => setForm({ ...form, client_id: v })}>
                <SelectTrigger data-testid="dossier-client-select"><SelectValue placeholder="Sélectionner un client" /></SelectTrigger>
                <SelectContent className="bg-white">
                  {clients.map((c) => <SelectItem key={c.id} value={c.id}>{c.nom}</SelectItem>)}
                </SelectContent>
              </Select>
              {clients.length === 0 && <p className="text-xs text-amber-600">Créez d'abord un client dans l'onglet Clients.</p>}
            </div>
          )}
          <div className="space-y-1.5">
            <Label>Nom de l'entreprise</Label>
            <Input value={form.nom_entreprise} onChange={(e) => setForm({ ...form, nom_entreprise: e.target.value })} data-testid="dossier-nom-input" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5"><Label>NEQ</Label>
              <Input value={form.neq} onChange={(e) => setForm({ ...form, neq: e.target.value })} data-testid="dossier-neq-input" /></div>
            <div className="space-y-1.5"><Label>Employés au Québec</Label>
              <Input type="number" value={form.nb_employes_quebec} onChange={(e) => setForm({ ...form, nb_employes_quebec: e.target.value })} data-testid="dossier-employes-input" /></div>
            <div className="space-y-1.5"><Label>Établissements</Label>
              <Input type="number" value={form.nb_etablissements} onChange={(e) => setForm({ ...form, nb_etablissements: e.target.value })} data-testid="dossier-etablissements-input" /></div>
            <div className="space-y-1.5"><Label>Date d'attestation d'inscription</Label>
              <Input type="date" value={form.date_attestation_inscription} onChange={(e) => setForm({ ...form, date_attestation_inscription: e.target.value })} data-testid="dossier-attestation-input" /></div>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={submit} disabled={busy || !form.nom_entreprise} data-testid="dossier-create-submit" className="bg-[#0F2B48] hover:bg-[#0F2B48]/90">
            {busy ? "Création…" : "Créer le dossier"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const isPro = user?.account_type === "PRO";
  const [dossiers, setDossiers] = useState([]);
  const [clients, setClients] = useState([]);
  const [filterClient, setFilterClient] = useState("all");
  const navigate = useNavigate();

  const load = async () => {
    const [d, c] = await Promise.all([
      api.get("/dossiers"),
      isPro ? api.get("/clients") : Promise.resolve({ data: [] }),
    ]);
    setDossiers(d.data); setClients(c.data);
  };
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() =>
    filterClient === "all" ? dossiers : dossiers.filter((d) => d.client_id === filterClient),
    [dossiers, filterClient]);

  const clientName = (id) => clients.find((c) => c.id === id)?.nom;
  const nearest = filtered.find((d) => d.jours_restants_module1 != null);

  return (
    <Layout>
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h1 className="font-display text-3xl font-extrabold text-[#0F2B48]">Tableau de bord</h1>
          <p className="text-slate-500">
            {isPro ? "Vos dossiers clients, triés par échéance légale la plus proche." : "Votre dossier de francisation, guidé étape par étape."}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isPro && (
            <Select value={filterClient} onValueChange={setFilterClient}>
              <SelectTrigger className="w-48 bg-white" data-testid="client-filter-select"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-white">
                <SelectItem value="all">Tous les clients</SelectItem>
                {clients.map((c) => <SelectItem key={c.id} value={c.id}>{c.nom}</SelectItem>)}
              </SelectContent>
            </Select>
          )}
          <CreateDossierDialog clients={clients} isPro={isPro} onCreated={() => load()} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Card className="p-5 flex items-center gap-4">
          <div className="h-11 w-11 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center"><Layers size={22} /></div>
          <div><div className="text-2xl font-bold text-[#0F2B48]" data-testid="stat-dossiers">{filtered.length}</div><div className="text-xs text-slate-500">Dossiers actifs</div></div>
        </Card>
        <Card className="p-5 flex items-center gap-4">
          <div className="h-11 w-11 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center"><AlarmClock size={22} /></div>
          <div>
            <div className="text-2xl font-bold text-[#0F2B48]">{nearest ? `${nearest.jours_restants_module1} j` : "—"}</div>
            <div className="text-xs text-slate-500">Échéance la plus proche{nearest ? ` · ${nearest.nom_entreprise}` : ""}</div>
          </div>
        </Card>
        <Card className="p-5 flex items-center gap-4">
          <div className="h-11 w-11 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center"><Building2 size={22} /></div>
          <div><div className="text-2xl font-bold text-[#0F2B48]">{isPro ? clients.length : 1}</div><div className="text-xs text-slate-500">{isPro ? "Clients" : "Entreprise"}</div></div>
        </Card>
      </div>

      {filtered.length === 0 ? (
        <Card className="p-12 text-center" data-testid="empty-state">
          <FolderOpen className="mx-auto text-slate-300 mb-3" size={40} />
          <h3 className="font-display font-bold text-slate-700">Aucun dossier</h3>
          <p className="text-sm text-slate-500 mb-4">Créez votre premier dossier de francisation pour commencer.</p>
          <div className="flex justify-center"><CreateDossierDialog clients={clients} isPro={isPro} onCreated={() => load()} /></div>
        </Card>
      ) : (
        <div className="space-y-3">
          {filtered.map((d) => {
            const analyse = d.stages?.find((s) => s.key === "analyse");
            return (
              <Card key={d.id} data-testid={`dossier-row-${d.id}`}
                className="p-5 flex flex-wrap items-center justify-between gap-4 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => navigate(`/dossier/${d.id}`)}>
                <div className="min-w-[200px]">
                  <div className="flex items-center gap-2">
                    <h3 className="font-display font-bold text-[#0F2B48]">{d.nom_entreprise}</h3>
                    {isPro && d.client_id && <span className="text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">{clientName(d.client_id)}</span>}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5 font-mono">NEQ {d.neq || "—"} · {d.nb_employes_quebec} employés</div>
                </div>
                <div className="flex items-center gap-3">
                  {analyse && <StatusBadge statut={analyse.statut} testId={`dossier-${d.id}-analyse-status`} />}
                  <div className={`text-xs font-medium px-3 py-1.5 rounded-lg border ${urgencyCls(d.urgence_module1)}`} data-testid={`dossier-${d.id}-echeance`}>
                    {d.echeance_module1
                      ? <>Analyse due le {d.echeance_module1} · <b>{d.jours_restants_module1 < 0 ? `en retard de ${Math.abs(d.jours_restants_module1)} j` : `${d.jours_restants_module1} j`}</b></>
                      : "Échéance non définie"}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </Layout>
  );
}
