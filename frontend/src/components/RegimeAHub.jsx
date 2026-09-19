import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ParcoursAElements } from "@/components/ParcoursAElements";
import { GanttParcoursA } from "@/components/GanttParcoursA";
import { KanbanBoard } from "@/components/KanbanBoard";
import { AmorcePanel } from "@/components/AmorcePanel";
import { AnalyseTab } from "@/components/AnalyseTab";
import { AuditLog } from "@/components/AuditLog";
import { ArrowLeft, ClipboardCheck, MessageSquareWarning, Smartphone, ScanSearch, History, List, GanttChartSquare } from "lucide-react";

function HubCard({ testid, icon: Icon, title, desc, meta, onOpen }) {
  return (
    <button onClick={onOpen} data-testid={testid}
      className="text-left rounded-2xl border-2 border-indigo-100 hover:border-indigo-400 bg-white/80 p-6 transition-all duration-200 h-full">
      <div className="flex items-center gap-3 mb-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700"><Icon size={24} strokeWidth={1.8} /></div>
        <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-full px-3 py-1">{meta}</span>
      </div>
      <h3 className="font-display text-xl font-extrabold text-[#0F2B48]">{title}</h3>
      <p className="text-sm text-slate-500 mt-2 leading-snug">{desc}</p>
    </button>
  );
}

const BackBar = ({ label, onBack }) => (
  <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-4" data-testid="regimea-back-hub">
    <ArrowLeft size={16} /> Retour au choix de parcours{label ? ` · ${label}` : ""}
  </button>
);

export const RegimeAHub = ({ dossier, onUpdated, reload }) => {
  const [view, setView] = useState("hub");
  const [aView, setAView] = useState("liste");

  if (view === "A") {
    return (
      <div data-testid="parcours-a-view">
        <BackBar label="Parcours A — Mise en conformité" onBack={() => setView("hub")} />
        <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 mb-4">
          <button onClick={() => setAView("liste")} data-testid="parcoursa-view-liste"
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${aView === "liste" ? "bg-white shadow-sm text-[#0F2B48]" : "text-slate-500 hover:text-slate-700"}`}>
            <List size={15} /> Liste des obligations
          </button>
          <button onClick={() => setAView("gantt")} data-testid="parcoursa-view-gantt"
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${aView === "gantt" ? "bg-white shadow-sm text-[#0F2B48]" : "text-slate-500 hover:text-slate-700"}`}>
            <GanttChartSquare size={15} /> Diagramme de Gantt
          </button>
        </div>
        {aView === "liste"
          ? <ParcoursAElements dossier={dossier} onUpdated={onUpdated} onGoAnalyse={() => setView("analyse")} />
          : <GanttParcoursA dossier={dossier} onUpdated={onUpdated} />}
      </div>
    );
  }
  if (view === "B") {
    return (
      <div data-testid="parcours-b-view">
        <BackBar label="Parcours B — Traitement d'une plainte" onBack={() => setView("hub")} />
        <KanbanBoard dossier={dossier} onUpdated={onUpdated} />
      </div>
    );
  }
  if (view === "amorce") {
    return (<div><BackBar onBack={() => setView("hub")} /><AmorcePanel dossier={dossier} /></div>);
  }
  if (view === "analyse") {
    return (<div><BackBar onBack={() => setView("hub")} /><AnalyseTab dossier={dossier} onMesureAdded={reload} /></div>);
  }
  if (view === "journal") {
    return (<div><BackBar onBack={() => setView("hub")} /><AuditLog dossierId={dossier.id} /></div>);
  }

  const aDone = dossier.parcours_a_traites || 0;
  const aTotal = dossier.parcours_a_total || 0;
  const plaintOuverte = dossier.plainte_ouverte;

  return (
    <div className="space-y-6" data-testid="regimea-hub">
      <div className="rounded-xl bg-indigo-50 border border-indigo-200 px-4 py-3 text-indigo-800 text-sm">
        Entreprise de moins de 25 employés. Choisissez un parcours ci-dessous — vous pouvez ouvrir l'un ou l'autre à tout moment.
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <HubCard testid="hub-parcours-a" icon={ClipboardCheck}
          title="Parcours A — Mise en conformité"
          desc="Rendez votre entreprise conforme aux obligations universelles de la Charte, obligation par obligation, avec preuves à l'appui."
          meta={`${aDone}/${aTotal} éléments`}
          onOpen={() => setView("A")} />
        <HubCard testid="hub-parcours-b" icon={MessageSquareWarning}
          title="Parcours B — Traitement d'une plainte"
          desc="Suivez la procédure de traitement d'une plainte de l'OQLF, de la communication initiale jusqu'à sa résolution."
          meta={plaintOuverte ? "Plainte en cours" : "Aucune plainte"}
          onOpen={() => setView("B")} />
      </div>
      <div className="flex flex-wrap items-center gap-4 pt-1">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Outils</span>
        <button onClick={() => setView("amorce")} className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-[#2563EB]" data-testid="hub-tool-amorce"><Smartphone size={15} /> Amorce mobile</button>
        <button onClick={() => setView("analyse")} className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-[#2563EB]" data-testid="hub-tool-analyse"><ScanSearch size={15} /> Analyse documentaire</button>
        <button onClick={() => setView("journal")} className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-[#2563EB]" data-testid="hub-tool-journal"><History size={15} /> Journal d'audit</button>
      </div>
    </div>
  );
};
