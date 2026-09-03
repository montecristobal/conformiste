import { useEffect, useState } from "react";
import { Layout } from "@/components/Layout";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Plus, Building2 } from "lucide-react";

export default function ClientsPage() {
  const [clients, setClients] = useState([]);
  const [counts, setCounts] = useState({});
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ nom: "", neq: "", contact: "" });
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const [{ data: cs }, { data: ds }] = await Promise.all([api.get("/clients"), api.get("/dossiers")]);
    setClients(cs);
    const map = {};
    ds.forEach((d) => { if (d.client_id) map[d.client_id] = (map[d.client_id] || 0) + 1; });
    setCounts(map);
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/clients", form);
      toast.success("Client créé");
      setOpen(false); setForm({ nom: "", neq: "", contact: "" });
      load();
    } catch (e) { toast.error("Erreur"); }
    finally { setBusy(false); }
  };

  return (
    <Layout>
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl font-extrabold text-[#0F2B48]">Clients</h1>
          <p className="text-slate-500">Gérez vos clients — chaque dossier est cloisonné par client.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="create-client-button" className="bg-[#0F2B48] hover:bg-[#0F2B48]/90"><Plus size={17} className="mr-1" /> Nouveau client</Button>
          </DialogTrigger>
          <DialogContent className="bg-white">
            <DialogHeader><DialogTitle>Nouveau client</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-1.5"><Label>Nom du client</Label>
                <Input value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })} data-testid="client-nom-input" /></div>
              <div className="space-y-1.5"><Label>NEQ</Label>
                <Input value={form.neq} onChange={(e) => setForm({ ...form, neq: e.target.value })} data-testid="client-neq-input" /></div>
              <div className="space-y-1.5"><Label>Contact</Label>
                <Input value={form.contact} onChange={(e) => setForm({ ...form, contact: e.target.value })} data-testid="client-contact-input" /></div>
            </div>
            <DialogFooter>
              <Button onClick={submit} disabled={busy || !form.nom} data-testid="client-create-submit" className="bg-[#0F2B48] hover:bg-[#0F2B48]/90">
                {busy ? "Création…" : "Créer"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {clients.length === 0 ? (
        <Card className="p-12 text-center" data-testid="clients-empty">
          <Building2 className="mx-auto text-slate-300 mb-3" size={40} />
          <h3 className="font-display font-bold text-slate-700">Aucun client</h3>
          <p className="text-sm text-slate-500">Ajoutez un client pour créer ses dossiers de francisation.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {clients.map((c) => (
            <Card key={c.id} className="p-5" data-testid={`client-card-${c.id}`}>
              <div className="h-10 w-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center mb-3"><Building2 size={20} /></div>
              <h3 className="font-display font-bold text-[#0F2B48]">{c.nom}</h3>
              <p className="text-xs text-slate-500 font-mono mt-0.5">NEQ {c.neq || "—"}</p>
              {c.contact && <p className="text-xs text-slate-500 mt-0.5">{c.contact}</p>}
              <div className="mt-3 text-xs text-slate-600 bg-slate-50 rounded-lg px-3 py-1.5 inline-block">
                {counts[c.id] || 0} dossier(s)
              </div>
            </Card>
          ))}
        </div>
      )}
    </Layout>
  );
}
