import { useState } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ShieldCheck, ArrowRight, ArrowLeft, ScrollText, Building2, MessageSquareWarning, Info,
} from "lucide-react";

const STEPS = [
  {
    num: 1, icon: ScrollText,
    titre: "Obligations universelles",
    desc: "Mise en conformité aux articles exécutoires de la Charte (langue du travail, du commerce et des affaires) : communications, contrats, factures, affichage, produits, nom d'entreprise… (U1 à U18).",
  },
  {
    num: 2, icon: Building2,
    titre: "Déclaration au REQ",
    desc: "Pour les entreprises d'au moins 5 employés : obligation de déclarer au registre la proportion d'employés qui ne peuvent communiquer en français (art. 149 de la Charte et art. 33, 10° de la Loi P‑44.1).",
  },
  {
    num: 3, icon: MessageSquareWarning,
    titre: "Traitement d'une plainte",
    desc: "En cas de plainte à l'Office pour non‑conformité à un article exécutoire : parcours guidé pour régler la situation. (Bientôt disponible.)",
    soon: true,
  },
];

export default function RegimeAIntro() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [nb, setNb] = useState("");

  if (user) return <Navigate to="/dashboard" replace />;
  const taille = location.state?.taille || "moins_25";

  const nbNum = nb === "" ? null : Math.max(0, Math.min(24, parseInt(nb, 10) || 0));

  return (
    <div className="relative min-h-screen form-grid-bg overflow-hidden">
      <div className="relative z-10">
        <header className="max-w-[1000px] mx-auto px-5 py-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="text-[#2563EB]" size={24} />
            <span className="font-display font-extrabold text-xl text-[#0F2B48] tracking-tight">CONFORMISTE</span>
          </div>
          <Button variant="ghost" onClick={() => navigate("/login")} className="text-slate-600" data-testid="intro-login-button">Se connecter</Button>
        </header>

        <div className="max-w-[1000px] mx-auto px-5 pt-8 pb-20">
          <button onClick={() => navigate("/")} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-5" data-testid="intro-back">
            <ArrowLeft size={16} /> Choix de la taille
          </button>

          <span className="inline-flex items-center gap-2 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-full px-4 py-1.5 mb-5">
            Parcours PME · moins de 25 employés
          </span>
          <h1 className="font-display text-4xl sm:text-5xl font-extrabold tracking-tight text-[#0F2B48] leading-[1.05]">
            Un parcours adapté aux petites entreprises
          </h1>

          <div className="mt-5 flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-amber-800 max-w-3xl" data-testid="intro-info">
            <Info size={18} className="mt-0.5 shrink-0" />
            <p className="text-sm">
              Une entreprise de moins de 25 employés <b>n'est pas suivie par l'Office</b> dans un processus de
              francisation — <b>sauf en cas de plainte</b> pour non‑conformité à un article exécutoire de la Charte.
              CONFORMISTE vous aide à rester conforme et à réagir si une plainte survient.
            </p>
          </div>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
            {STEPS.map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.num} className={`rounded-2xl border p-5 bg-white/80 ${s.soon ? "opacity-70" : ""}`} data-testid={`intro-step-${s.num}`}>
                  <div className="flex items-center gap-3 mb-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700">
                      <Icon size={20} strokeWidth={1.8} />
                    </div>
                    <span className="text-[11px] font-mono font-semibold px-1.5 py-0.5 rounded bg-[#0F2B48] text-white">Étape {s.num}</span>
                    {s.soon && <span className="text-[10px] text-slate-400 border border-slate-200 rounded-full px-2 py-0.5">à venir</span>}
                  </div>
                  <h3 className="font-display font-bold text-[#0F2B48]">{s.titre}</h3>
                  <p className="text-sm text-slate-500 mt-1.5 leading-snug">{s.desc}</p>
                </div>
              );
            })}
          </div>

          <div className="mt-8 max-w-md">
            <Label className="text-sm font-semibold text-slate-700">Combien d'employés au Québec, exactement ?</Label>
            <p className="text-xs text-slate-500 mb-2">Nécessaire pour déterminer l'obligation de déclaration au REQ (seuil de 5 employés).</p>
            <Input type="number" min={0} max={24} value={nb} onChange={(e) => setNb(e.target.value)}
              placeholder="Ex. 8" data-testid="intro-nb-employes" className="max-w-[160px]" />
            {nbNum != null && nbNum >= 5 && (
              <p className="text-xs text-indigo-600 mt-1" data-testid="intro-req-hint">Déclaration au REQ requise (5 employés et plus).</p>
            )}
          </div>

          <div className="mt-8 flex flex-col sm:flex-row items-center gap-3">
            <Button size="lg" disabled={nbNum == null} data-testid="intro-continue-button"
              onClick={() => navigate("/register", { state: { account_type: "SOLO", taille, nb_employes: nbNum } })}
              className="bg-[#0F2B48] hover:bg-[#0F2B48]/90 w-full sm:w-auto">
              Continuer <ArrowRight size={18} className="ml-2" />
            </Button>
            <span className="text-sm text-slate-500">
              Vous avez déjà un compte ?{" "}
              <button className="text-[#2563EB] font-medium hover:underline" onClick={() => navigate("/login")} data-testid="intro-login-link">Connectez-vous</button>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
