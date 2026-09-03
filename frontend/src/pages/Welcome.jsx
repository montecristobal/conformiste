import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ShieldCheck, User, Building2, Check, ArrowRight, FileText } from "lucide-react";

const FEATURES = {
  SOLO: [
    "Un seul dossier d'entreprise, guidé étape par étape",
    "Conseils adaptés à vos intérêts tout au long du processus",
    "Idéal pour les entreprises de moins de 100 employés",
    "Assistant de conformité et rappels d'échéances légales",
  ],
  PRO: [
    "Gestion de plusieurs dossiers clients en parallèle",
    "Cloisonnement strict des données par client",
    "Vue d'ensemble des échéances de tout le portefeuille",
    "Espace de travail conçu pour les consultants en francisation",
  ],
};

function ModeCard({ mode, selected, onSelect }) {
  const isPro = mode === "PRO";
  const Icon = isPro ? Building2 : User;
  return (
    <button
      data-testid={`welcome-mode-${mode.toLowerCase()}-button`}
      onClick={() => onSelect(mode)}
      className={`text-left rounded-2xl border-2 p-6 transition-all duration-300 ${
        selected
          ? "border-[#2563EB] bg-white shadow-xl shadow-blue-500/10 scale-[1.01]"
          : "border-slate-200 bg-white/70 hover:border-slate-300"
      }`}
    >
      <div className="flex items-center justify-between mb-4">
        <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${isPro ? "bg-blue-100 text-blue-700" : "bg-emerald-100 text-emerald-700"}`}>
          <Icon size={24} />
        </div>
        {selected && <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#2563EB] text-white"><Check size={15} /></span>}
      </div>
      <h3 className="font-display text-2xl font-extrabold text-[#0F2B48]">Version {mode}</h3>
      <p className="text-sm text-slate-500 mt-1 mb-4">
        {isPro ? "Consultant·e en francisation — plusieurs clients." : "Entreprise gérant son propre dossier."}
      </p>
      <ul className="space-y-2">
        {FEATURES[mode].map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-slate-600">
            <Check size={16} className={`mt-0.5 shrink-0 ${isPro ? "text-blue-600" : "text-emerald-600"}`} /> {f}
          </li>
        ))}
      </ul>
    </button>
  );
}

export default function Welcome() {
  const [mode, setMode] = useState("SOLO");
  const navigate = useNavigate();
  const { user } = useAuth();

  if (user) return <Navigate to="/dashboard" replace />;

  return (
    <div className="min-h-screen paper-bg">
      <header className="max-w-[1200px] mx-auto px-5 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="text-[#2563EB]" size={24} />
          <span className="font-display font-extrabold text-xl text-[#0F2B48] tracking-tight">CONFORMISTE</span>
        </div>
        <Button variant="ghost" onClick={() => navigate("/login")} data-testid="header-login-button" className="text-slate-600">
          Se connecter
        </Button>
      </header>

      <div className="max-w-[1200px] mx-auto px-5 pt-6 pb-20">
        <div className="max-w-3xl animate-fade-up">
          <span className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-full px-3 py-1 mb-5">
            <FileText size={13} /> Charte de la langue française du Québec — Loi 96
          </span>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#0F2B48] leading-[1.05]">
            La conformité en francisation,<br />gérée comme une déclaration.
          </h1>
          <p className="mt-5 text-lg text-slate-600 max-w-2xl">
            CONFORMISTE numérise vos dossiers de francisation OQLF — de l'analyse de la situation
            linguistique au programme de francisation — avec échéances légales, journal d'audit et
            exports PDF prêts à transmettre.
          </p>
        </div>

        <div className="mt-12">
          <h2 className="font-display text-lg font-bold text-slate-700 mb-4">Choisissez votre version</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <ModeCard mode="SOLO" selected={mode === "SOLO"} onSelect={setMode} />
            <ModeCard mode="PRO" selected={mode === "PRO"} onSelect={setMode} />
          </div>
          <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
            <Button size="lg" data-testid="welcome-continue-button"
              onClick={() => navigate("/register", { state: { account_type: mode } })}
              className="bg-[#0F2B48] hover:bg-[#0F2B48]/90 w-full sm:w-auto">
              Continuer en version {mode} <ArrowRight size={18} className="ml-2" />
            </Button>
            <span className="text-sm text-slate-500">
              Vous avez déjà un compte ?{" "}
              <button className="text-[#2563EB] font-medium hover:underline" onClick={() => navigate("/login")} data-testid="welcome-login-link">
                Connectez-vous
              </button>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
