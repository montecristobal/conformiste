import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { ShieldCheck, ArrowRight, Check, Users, Building2, Building, Scale } from "lucide-react";

const OPTIONS = [
  {
    key: "moins_25", regime: "A", icon: Users,
    titre: "Moins de 25 employés",
    tag: "Obligations universelles",
    desc: "Votre entreprise est assujettie aux obligations générales de la Charte (langue du travail, du commerce et des affaires), sans parcours de francisation ni certificat.",
  },
  {
    key: "25_99", regime: "B", icon: Building2,
    titre: "Entre 25 et 99 employés",
    tag: "Parcours de francisation",
    desc: "Votre entreprise doit s'inscrire à l'Office et suivre le parcours de francisation (analyse de la situation linguistique, programme, certificat).",
  },
  {
    key: "100_plus", regime: "B", icon: Building,
    titre: "100 employés et plus",
    tag: "Francisation + comité",
    desc: "Parcours de francisation complet, avec en plus l'obligation de constituer un comité de francisation.",
  },
];

function SizeCard({ opt, selected, onSelect }) {
  const Icon = opt.icon;
  const isA = opt.regime === "A";
  const accent = isA
    ? { ring: "border-indigo-500 ring-indigo-500/10", tint: "bg-indigo-50/60", idle: "border-indigo-100 hover:border-indigo-300", iconBox: "bg-indigo-100 text-indigo-700", check: "bg-indigo-500", tag: "bg-indigo-100 text-indigo-700" }
    : { ring: "border-[#2563EB] ring-blue-500/10", tint: "bg-blue-50/50", idle: "border-blue-100 hover:border-blue-300", iconBox: "bg-blue-100 text-blue-700", check: "bg-[#2563EB]", tag: "bg-blue-100 text-blue-700" };
  return (
    <button
      data-testid={`size-option-${opt.key}`}
      onClick={() => onSelect(opt.key)}
      className={`relative text-left rounded-2xl border-2 p-6 transition-all duration-300 h-full ${
        selected ? `${accent.ring} ${accent.tint} shadow-xl shadow-slate-500/5 ring-4` : `${accent.idle} bg-white/70`
      }`}
    >
      <div className="flex items-center justify-between mb-4">
        <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${accent.iconBox}`}>
          <Icon size={24} strokeWidth={1.8} />
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${accent.tag}`}>{opt.tag}</span>
          {selected && <span className={`flex h-6 w-6 items-center justify-center rounded-full text-white ${accent.check}`}><Check size={15} /></span>}
        </div>
      </div>
      <h3 className="font-display text-xl font-extrabold text-[#0F2B48]">{opt.titre}</h3>
      <p className="text-sm text-slate-500 mt-2 leading-snug">{opt.desc}</p>
    </button>
  );
}

export default function SizeGate() {
  const [taille, setTaille] = useState("");
  const navigate = useNavigate();
  const { user } = useAuth();

  if (user) return <Navigate to="/dashboard" replace />;

  return (
    <div className="relative min-h-screen form-grid-bg overflow-hidden">
      <div className="relative z-10">
        <header className="max-w-[1100px] mx-auto px-5 py-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="text-[#2563EB]" size={24} />
            <span className="font-display font-extrabold text-xl text-[#0F2B48] tracking-tight">CONFORMISTE</span>
          </div>
          <Button variant="ghost" onClick={() => navigate("/login")} data-testid="size-header-login-button" className="text-slate-600">
            Se connecter
          </Button>
        </header>

        <div className="max-w-[1100px] mx-auto px-5 pt-10 pb-20">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-2 text-sm font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-full px-4 py-1.5 shadow-sm mb-5">
              <Scale size={16} /> Charte de la langue française du Québec
            </span>
            <h1 className="font-display text-4xl sm:text-5xl font-extrabold tracking-tight text-[#0F2B48] leading-[1.05]">
              Combien d'employés votre entreprise compte-t-elle au Québec&nbsp;?
            </h1>
            <p className="mt-4 text-lg text-slate-600">
              Vos obligations sous la Charte dépendent directement de votre taille. Cette réponse oriente
              votre dossier vers le bon régime — nous ne vous proposerons que ce qui vous concerne réellement.
            </p>
          </div>

          <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-5" data-testid="size-options">
            {OPTIONS.map((opt) => (
              <SizeCard key={opt.key} opt={opt} selected={taille === opt.key} onSelect={setTaille} />
            ))}
          </div>

          <div className="mt-8 flex flex-col sm:flex-row items-center gap-3">
            <Button size="lg" disabled={!taille} data-testid="size-continue-button"
              onClick={() => navigate(taille === "moins_25" ? "/parcours-pme" : "/welcome", { state: { taille } })}
              className="bg-[#0F2B48] hover:bg-[#0F2B48]/90 w-full sm:w-auto">
              Continuer <ArrowRight size={18} className="ml-2" />
            </Button>
            <span className="text-sm text-slate-500">
              Vous avez déjà un compte ?{" "}
              <button className="text-[#2563EB] font-medium hover:underline" onClick={() => navigate("/login")} data-testid="size-login-link">
                Connectez-vous
              </button>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
