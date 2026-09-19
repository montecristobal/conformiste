import { useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Search, Building2, Users, Save, Loader2, CheckCircle2, Info } from "lucide-react";

function Toggle({ checked, onChange, title, desc, testid }) {
  return (
    <button type="button" onClick={() => onChange(!checked)} data-testid={testid}
      className={`text-left rounded-xl border-2 p-3 transition-all ${checked ? "border-indigo-400 bg-indigo-50" : "border-slate-200 bg-white hover:border-slate-300"}`}>
      <div className="flex items-center gap-2">
        <span className={`h-4 w-4 rounded border flex items-center justify-center ${checked ? "bg-indigo-600 border-indigo-600" : "border-slate-300"}`}>
          {checked && <CheckCircle2 size={12} className="text-white" />}
        </span>
        <span className="text-sm font-semibold text-[#0F2B48]">{title}</span>
      </div>
      {desc && <p className="text-[11px] text-slate-500 mt-1 ml-6">{desc}</p>}
    </button>
  );
}

export const ParcoursAProfil = ({ dossier, onUpdated }) => {
  const p = dossier.parcours_a_profil || {};
  const [neq, setNeq] = useState(p.neq || dossier.neq || "");
  const [nomLegal, setNomLegal] = useState(p.nom_legal || dossier.nom_entreprise || "");
  const [marques, setMarques] = useState((p.marques || []).join(", "));
  const [syndicat, setSyndicat] = useState(!!p.syndicat);
  const [vendProduits, setVendProduits] = useState(!!p.vend_produits);
  const [vendJouets, setVendJouets] = useState(!!p.vend_jouets);
  const [immo, setImmo] = useState(!!p.immo_residentiel);
  const [nbEmployes, setNbEmployes] = useState(p.nb_employes ?? dossier.nb_employes_quebec ?? "");
  const [nbFrancais, setNbFrancais] = useState(p.nb_francais ?? "");
  const [looking, setLooking] = useState(false);
  const [busy, setBusy] = useState(false);

  const total = parseInt(nbEmployes, 10) || 0;
  const franc = Math.max(0, Math.min(total, parseInt(nbFrancais, 10) || 0));
  const nonFranco = Math.max(0, total - franc);
  const proportion = total ? Math.round((nonFranco / total) * 1000) / 10 : 0;
  const reqRequise = total >= 5;

  const lookup = async () => {
    const clean = (neq || "").trim();
    if (!/^\d{9,10}$/.test(clean)) { toast.error("NEQ invalide : 9 ou 10 chiffres."); return; }
    setLooking(true);
    try {
      const { data } = await api.get(`/req/lookup?neq=${clean}`);
      setNomLegal(data.nom_entreprise || nomLegal);
      const m = data.autres_noms || [];
      if (m.length) setMarques(m.join(", "));
      toast.success("Informations récupérées du registre (démonstration)");
    } catch (e) { toast.error("Recherche NEQ impossible"); } finally { setLooking(false); }
  };

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.put(`/dossiers/${dossier.id}/parcours-a/profil`, {
        neq: (neq || "").trim(), nom_legal: nomLegal,
        marques: marques.split(",").map((x) => x.trim()).filter(Boolean),
        syndicat, vend_produits: vendProduits, vend_jouets: vendJouets, immo_residentiel: immo,
        nb_employes: total, nb_francais: franc,
      });
      toast.success("Profil enregistré — obligations applicables mises à jour");
      onUpdated(data);
    } catch (e) { toast.error("Erreur lors de l'enregistrement"); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-5" data-testid="parcoursa-profil">
      <div className="rounded-xl bg-indigo-50 border border-indigo-200 px-4 py-3 text-indigo-800 text-sm">
        Commençons par identifier votre entreprise et son contexte. Vos réponses déterminent quelles obligations
        de la Charte s'appliquent réellement à vous — inutile d'évaluer ce qui ne vous concerne pas.
      </div>

      <Card className="p-5 space-y-4">
        <div className="flex items-center gap-2"><Building2 size={18} className="text-indigo-600" />
          <h3 className="font-display text-lg font-bold text-[#0F2B48]">1. Identification (NEQ)</h3></div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5 flex-1 min-w-[180px]">
            <Label className="text-xs">Numéro d'entreprise du Québec (NEQ)</Label>
            <Input value={neq} onChange={(e) => setNeq(e.target.value)} placeholder="9 ou 10 chiffres" data-testid="profil-neq-input" />
          </div>
          <Button variant="outline" onClick={lookup} disabled={looking} data-testid="profil-neq-lookup">
            {looking ? <Loader2 size={15} className="mr-1 animate-spin" /> : <Search size={15} className="mr-1" />} Récupérer
          </Button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5"><Label className="text-xs">Nom légal</Label>
            <Input value={nomLegal} onChange={(e) => setNomLegal(e.target.value)} data-testid="profil-nom-input" /></div>
          <div className="space-y-1.5"><Label className="text-xs">Marques de commerce / autres noms (séparés par des virgules)</Label>
            <Input value={marques} onChange={(e) => setMarques(e.target.value)} data-testid="profil-marques-input" /></div>
        </div>
        <p className="text-[11px] text-slate-400 flex items-start gap-1.5"><Info size={12} className="mt-0.5 shrink-0" /> Source de démonstration pour l'instant ; sera remplacée par le registre officiel (REQ) lorsque l'accès sera disponible.</p>
      </Card>

      <Card className="p-5 space-y-4">
        <h3 className="font-display text-lg font-bold text-[#0F2B48]">2. Contexte de l'entreprise</h3>
        <p className="text-xs text-slate-500 -mt-2">Ces réponses activent ou retirent des obligations du parcours.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Toggle checked={syndicat} onChange={setSyndicat} testid="profil-syndicat"
            title="Présence d'un syndicat / association de travailleurs"
            desc="Active les obligations liées aux conventions collectives, aux communications de l'association et à l'assurance collective (U3, U7, U8)." />
          <Toggle checked={vendProduits} onChange={setVendProduits} testid="profil-produits"
            title="Vend des produits au Québec"
            desc="Active l'étiquetage/emballage, les catalogues/brochures et les factures/reçus (U10, U11, U14)." />
          <Toggle checked={vendJouets} onChange={setVendJouets} testid="profil-jouets"
            title="Vend des jouets ou des jeux"
            desc="Active l'obligation sur les inscriptions des jouets et jeux (U17)." />
          <Toggle checked={immo} onChange={setImmo} testid="profil-immo"
            title="Loue ou vend de l'immobilier résidentiel"
            desc="Active l'obligation sur les contrats d'immeuble résidentiel (U18)." />
        </div>
      </Card>

      <Card className="p-5 space-y-4">
        <div className="flex items-center gap-2"><Users size={18} className="text-indigo-600" />
          <h3 className="font-display text-lg font-bold text-[#0F2B48]">3. Effectifs et français (préparatoire)</h3></div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <div className="space-y-1.5"><Label className="text-xs">Nombre total d'employés au Québec</Label>
            <Input type="number" min={0} value={nbEmployes} onChange={(e) => setNbEmployes(e.target.value)} data-testid="profil-nb-employes" /></div>
          <div className="space-y-1.5"><Label className="text-xs">Pouvant s'exprimer en français</Label>
            <Input type="number" min={0} max={total} value={nbFrancais} onChange={(e) => setNbFrancais(e.target.value)} data-testid="profil-nb-francais" /></div>
          <div className="space-y-1.5"><Label className="text-xs">Proportion NE pouvant PAS communiquer en français</Label>
            <div className="h-10 flex items-center px-3 rounded-md border border-slate-200 bg-indigo-50 text-indigo-800 font-semibold" data-testid="profil-proportion">{nonFranco}/{total} · {proportion} %</div></div>
        </div>
        <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-amber-800">
          <Info size={14} className="mt-0.5 shrink-0" />
          <p className="text-xs">{reqRequise
            ? "Calcul préparatoire uniquement. Il sera reporté dans la déclaration au registre (REQ), mais rien n'est transmis sans l'accord explicite de l'entreprise à l'étape de déclaration."
            : "Moins de 5 employés : aucune déclaration de proportion n'est requise au registre (REQ)."}</p>
        </div>
      </Card>

      <div className="flex items-center gap-3">
        <Button onClick={save} disabled={busy} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid="profil-save">
          {busy ? <Loader2 size={15} className="mr-2 animate-spin" /> : <Save size={15} className="mr-2" />} Enregistrer le profil et continuer
        </Button>
        {p.completed && <span className="text-sm text-emerald-700 inline-flex items-center gap-1.5"><CheckCircle2 size={15} /> Profil enregistré</span>}
      </div>
    </div>
  );
};
