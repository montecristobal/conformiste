import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { ShieldCheck, File, Files, Check, ArrowRight, FileText, Scale, Layers,
  AlarmClock, FileDown, BookText, Lock, History, ListChecks } from "lucide-react";

const FEATURES_GRID = [
  { testId: "prefill", icon: FileText, titre: "Pré-remplissage guidé", desc: "Récupère les données existantes sur votre entreprise et les complète par une entrevue personnalisée." },
  { testId: "export-pdf", icon: FileDown, titre: "Export PDF fidèle", desc: "Documents reproduisant les formulaires officiels, prêts à transmettre à l'OQLF." },
  { testId: "catalogue", icon: BookText, titre: "Catalogue légal", desc: "Thèmes fondés sur le texte de loi, sans interprétation de l'Office." },
  { testId: "cloisonnement", icon: Lock, titre: "Cloisonnement des dossiers", desc: "Chaque dossier client est isolé — essentiel en mode PRO." },
  { testId: "journal", icon: History, titre: "Journal d'audit horodaté", desc: "Chaque action est consignée et horodatée, avec empreinte de vérification." },
  { testId: "pipeline", icon: ListChecks, titre: "Pipeline en 8 étapes", desc: "De l'inscription au maintien, suivez chaque étape et son statut." },
];

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
  const Icon = isPro ? Files : File;
  const accent = isPro
    ? { ring: "border-[#2563EB] ring-blue-500/10", tint: "bg-blue-50/50", idle: "border-blue-100 hover:border-blue-300", iconBox: "bg-blue-100 text-blue-700", check: "bg-[#2563EB]", bullet: "text-blue-600", tag: "bg-blue-100 text-blue-700" }
    : { ring: "border-emerald-500 ring-emerald-500/10", tint: "bg-emerald-50/50", idle: "border-emerald-100 hover:border-emerald-300", iconBox: "bg-emerald-100 text-emerald-700", check: "bg-emerald-500", bullet: "text-emerald-600", tag: "bg-emerald-100 text-emerald-700" };
  return (
    <button
      data-testid={`welcome-mode-${mode.toLowerCase()}-button`}
      onClick={() => onSelect(mode)}
      className={`relative text-left rounded-2xl border-2 p-6 transition-all duration-300 ${
        selected ? `${accent.ring} ${accent.tint} shadow-xl shadow-slate-500/5 scale-[1.01] ring-4` : `${accent.idle} bg-white/70`
      }`}
    >
      <div className="flex items-center justify-between mb-4">
        <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${accent.iconBox}`}>
          <Icon size={24} strokeWidth={1.8} />
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${accent.tag}`}>
            {isPro ? "Multi-clients" : "Dossier unique"}
          </span>
          {selected && <span className={`flex h-6 w-6 items-center justify-center rounded-full text-white ${accent.check}`}><Check size={15} /></span>}
        </div>
      </div>
      <h3 className="font-display text-2xl font-extrabold text-[#0F2B48]">Version {mode}</h3>
      <p className="text-sm text-slate-500 mt-1 mb-4">
        {isPro ? "Consultant·e en francisation — plusieurs clients." : "Entreprise gérant son propre dossier."}
      </p>
      <ul className="space-y-2">
        {FEATURES[mode].map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-slate-600">
            <Check size={16} className={`mt-0.5 shrink-0 ${accent.bullet}`} /> {f}
          </li>
        ))}
      </ul>
    </button>
  );
}

function DashboardPreview() {
  const rows = [
    { nom: "Boulangerie Lévesque inc.", neq: "1170928456", emp: 62, jours: 4, urg: "critical", statut: "en_cours" },
    { nom: "Groupe Techno-Nord", neq: "1149550031", emp: 148, jours: 21, urg: "approaching", statut: "soumis" },
    { nom: "Ateliers Rivière-du-Loup", neq: "1163009284", emp: 37, jours: 63, urg: "normal", statut: "accepte" },
  ];
  const urgCls = { critical: "bg-red-100 text-red-700 border-red-200", approaching: "bg-amber-100 text-amber-800 border-amber-200", normal: "bg-slate-100 text-slate-500 border-slate-200" };
  const dot = { en_cours: "bg-blue-500", soumis: "bg-amber-500", accepte: "bg-green-500" };
  const statutLabel = { en_cours: "En cours", soumis: "Soumis à l'OQLF", accepte: "Accepté" };
  return (
    <div className="relative">
      <div className="absolute -inset-4 bg-gradient-to-tr from-blue-100/40 to-transparent rounded-[28px] blur-2xl" aria-hidden />
      <div className="relative rounded-2xl border border-slate-200 bg-white shadow-2xl shadow-slate-900/10 overflow-hidden" data-testid="welcome-dashboard-preview">
        <div className="h-10 bg-[#0F2B48] flex items-center gap-2 px-4">
          <ShieldCheck size={15} className="text-blue-300" />
          <span className="text-white text-xs font-display font-bold tracking-tight">CONFORMISTE</span>
          <span className="ml-1 text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-blue-500 text-white">PRO</span>
          <div className="ml-auto flex gap-1.5">
            <span className="h-2 w-2 rounded-full bg-white/25" />
            <span className="h-2 w-2 rounded-full bg-white/25" />
          </div>
        </div>
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-[13px] font-display font-bold text-[#0F2B48]">Tableau de bord</div>
              <div className="text-[10px] text-slate-400">Trié par échéance légale la plus proche</div>
            </div>
            <div className="text-[10px] px-2 py-1 rounded-lg bg-[#0F2B48] text-white font-medium">+ Dossier</div>
          </div>
          <div className="grid grid-cols-3 gap-2 mb-3">
            {[["3", "Dossiers"], ["4 j", "Échéance"], ["3", "Clients"]].map(([v, l]) => (
              <div key={l} className="rounded-lg bg-slate-50 border border-slate-100 px-2 py-1.5">
                <div className="text-sm font-bold text-[#0F2B48]">{v}</div>
                <div className="text-[9px] text-slate-400">{l}</div>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            {rows.map((r) => (
              <div key={r.neq} className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 bg-white px-2.5 py-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className={`h-1.5 w-1.5 rounded-full ${dot[r.statut]}`} />
                    <span className="text-[11px] font-semibold text-slate-700 truncate">{r.nom}</span>
                  </div>
                  <div className="text-[9px] text-slate-400 font-mono mt-0.5">NEQ {r.neq} · {r.emp} empl. · {statutLabel[r.statut]}</div>
                </div>
                <span className={`shrink-0 text-[9px] font-medium px-2 py-1 rounded-md border ${urgCls[r.urg]}`}>{r.jours} j</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Welcome() {
  const [mode, setMode] = useState("SOLO");
  const navigate = useNavigate();
  const { user } = useAuth();

  if (user) return <Navigate to="/dashboard" replace />;

  return (
    <div className="relative min-h-screen form-grid-bg overflow-hidden">
      <div className="pointer-events-none fixed inset-0 z-0 select-none" aria-hidden data-testid="montreal-watermark">
        <img
          src="https://customer-assets-agu9un31.emergentagent.net/job_conformiste-core/artifacts/ngwf9ozc_IMG_3852.webp"
          alt=""
          className="absolute bottom-0 left-0 w-full h-[55%] object-cover object-bottom opacity-40"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#F6F8FB] via-[#F6F8FB]/60 to-transparent" />
      </div>
      <div className="relative z-10">
      <header className="max-w-[1200px] mx-auto px-5 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="text-[#2563EB]" size={24} />
          <span className="font-display font-extrabold text-xl text-[#0F2B48] tracking-tight">CONFORMISTE</span>
        </div>
        <Button variant="ghost" onClick={() => navigate("/login")} data-testid="header-login-button" className="text-slate-600">
          Se connecter
        </Button>
      </header>

      <div className="max-w-[1200px] mx-auto px-5 pt-6 pb-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-14 items-center">
          <div className="animate-fade-up">
            <div className="flex flex-wrap items-center gap-2 mb-5">
              <span className="inline-flex items-center gap-2 text-sm font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-full px-4 py-1.5 shadow-sm">
                <Scale size={16} /> Charte de la langue française du Québec
              </span>
              <span className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-full px-3 py-1">
                <Layers size={13} className="text-slate-400" /> 8 étapes · 2 modules officiels
              </span>
            </div>
            <h1 className="font-display text-4xl sm:text-5xl lg:text-[3.4rem] font-extrabold tracking-tight text-[#0F2B48] leading-[1.05]">
              Gestion des obligations linguistiques
            </h1>
            <p className="mt-5 text-lg text-slate-600 max-w-xl">
              CONFORMISTE est un gestionnaire de projet linguistique qui automatise le processus
              de conformité à la Charte, de l'inscription à la certification et plus encore.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-slate-500">
              <span className="flex items-center gap-2" data-testid="trust-badge-legal"><Scale size={16} className="text-blue-500" /> Simplifie la conformité à la loi</span>
              <span className="flex items-center gap-2" data-testid="trust-badge-sections"><ListChecks size={16} className="text-blue-500" /> Conseils et outils pour optimiser le processus</span>
              <span className="flex items-center gap-2" data-testid="trust-badge-security"><Lock size={16} className="text-blue-500" /> Dossiers cloisonnés & sécurisés</span>
            </div>
          </div>

          <div className="hidden lg:block animate-fade-up" style={{ animationDelay: "0.12s" }}>
            <DashboardPreview />
          </div>
        </div>

        <div className="mt-14">
          <h2 className="font-display text-lg font-bold text-slate-700 mb-4">Choisissez votre version</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <p className="text-sm font-medium text-slate-700 mb-2 flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Gérer vous-même votre dossier
              </p>
              <ModeCard mode="SOLO" selected={mode === "SOLO"} onSelect={setMode} />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-700 mb-2 flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-[#2563EB]" /> Un outil de suivi et de gestion pour les consultants
              </p>
              <ModeCard mode="PRO" selected={mode === "PRO"} onSelect={setMode} />
            </div>
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

        <div className="mt-16" data-testid="features-grid">
          <h2 className="font-display text-lg font-bold text-slate-700 mb-5">Ce que fait CONFORMISTE</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES_GRID.map((f) => (
              <div key={f.titre} className="rounded-xl border border-slate-200 bg-white/80 p-5 transition-colors hover:border-blue-300" data-testid={`feature-${f.testId}`}>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700 mb-3">
                  <f.icon size={20} strokeWidth={1.8} />
                </div>
                <h3 className="font-display font-bold text-[#0F2B48] text-[15px]">{f.titre}</h3>
                <p className="text-sm text-slate-500 mt-1 leading-snug">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
    </div>
  );
}
