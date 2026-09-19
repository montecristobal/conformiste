import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Building2, Info, ChevronDown, ChevronRight, Save, CheckCircle2, Lock } from "lucide-react";

function LegalItem({ item }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50/60" data-testid={`regimea-framework-${item.id}`}>
      <button onClick={() => setOpen((o) => !o)} className="w-full flex items-center gap-2 px-3 py-2 text-left">
        {open ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
        <span className="text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded bg-[#0F2B48] text-white">{item.article}</span>
        <span className="text-sm font-medium text-[#0F2B48]">{item.titre}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1">
          <p className="text-[13px] text-slate-600 whitespace-pre-line">{item.texte_loi}</p>
          <p className="text-[11px] text-slate-400 mt-2">{item.external_citation}</p>
        </div>
      )}
    </div>
  );
}

export const RegimeAReq = ({ dossier, onSaved }) => {
  const [framework, setFramework] = useState([]);
  const prep = dossier.parcours_a_profil?.req_preparatoire?.non_francophones;
  const [nb, setNb] = useState(
    dossier.req_declaration?.nb_employes_non_francophones ?? (prep != null ? String(prep) : ""));
  const [busy, setBusy] = useState(false);
  const total = dossier.nb_employes_quebec || 0;
  const requise = !!dossier.req_declaration_requise;
  const decl = dossier.req_declaration;

  useEffect(() => {
    api.get("/catalogue/regime-a-framework").then(({ data }) => setFramework(data)).catch(() => {});
  }, []);

  const nbNum = nb === "" ? 0 : Math.max(0, Math.min(total, parseInt(nb, 10) || 0));
  const proportion = total ? Math.round((nbNum / total) * 1000) / 10 : 0;

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.put(`/dossiers/${dossier.id}/req-declaration`, { nb_employes_non_francophones: nbNum });
      toast.success("Déclaration REQ enregistrée");
      onSaved?.(data);
    } catch (e) { toast.error("Erreur lors de l'enregistrement"); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-5" data-testid="regimea-req-panel">
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-2">
          <Building2 size={18} className="text-indigo-600" />
          <h3 className="font-display text-lg font-bold text-[#0F2B48]">Déclaration au registre (REQ)</h3>
        </div>
        <p className="text-sm text-slate-500">
          Les entreprises d'au moins 5 employés visées par l'article 149 de la Charte doivent déclarer au
          registre des entreprises (REQ) la proportion de leurs employés qui ne sont pas en mesure de communiquer
          en français (art. 33, 10° de la Loi sur la publicité légale des entreprises, P‑44.1).
        </p>

        {!requise ? (
          <div className="mt-4 flex items-start gap-2 rounded-xl bg-slate-50 border border-slate-200 px-4 py-3 text-slate-600" data-testid="regimea-req-not-applicable">
            <Lock size={16} className="mt-0.5 shrink-0" />
            <p className="text-sm">
              <b>Obligation non applicable</b> — votre entreprise compte {total} employé(s) au Québec (moins de 5).
              Aucune déclaration de proportion n'est requise. Vous pouvez tout de même consulter le cadre légal ci‑dessous.
            </p>
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
              <div className="space-y-1.5">
                <Label className="text-xs">Employés au Québec</Label>
                <Input value={total} disabled data-testid="regimea-req-total" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Ne pouvant communiquer en français</Label>
                <Input type="number" min={0} max={total} value={nb} onChange={(e) => setNb(e.target.value)} data-testid="regimea-req-input" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Proportion</Label>
                <div className="h-10 flex items-center px-3 rounded-md border border-slate-200 bg-indigo-50 text-indigo-800 font-semibold" data-testid="regimea-req-proportion">
                  {proportion} %
                </div>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={save} disabled={busy} className="bg-[#0F2B48] hover:bg-[#0F2B48]/90" data-testid="regimea-req-save">
                <Save size={15} className="mr-2" /> {busy ? "Enregistrement…" : "Enregistrer la déclaration"}
              </Button>
              {decl && (
                <span className="inline-flex items-center gap-1.5 text-sm text-emerald-700" data-testid="regimea-req-saved">
                  <CheckCircle2 size={15} /> {decl.nb_employes_non_francophones}/{decl.total_employes} · {decl.proportion_non_francophone} % — enregistré le {new Date(decl.updated_at).toLocaleDateString("fr-CA")}
                </span>
              )}
            </div>
            <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-amber-800">
              <Info size={14} className="mt-0.5 shrink-0" />
              <p className="text-xs">Aide‑mémoire interne. La déclaration officielle se fait auprès du Registraire des entreprises (REQ) ; CONFORMISTE ne transmet rien en votre nom.</p>
            </div>
          </div>
        )}
      </Card>

      <Card className="p-5">
        <h4 className="font-display font-bold text-[#0F2B48] mb-3">Cadre légal</h4>
        <div className="space-y-2">
          {framework.map((item) => <LegalItem key={item.id} item={item} />)}
        </div>
      </Card>
    </div>
  );
};
