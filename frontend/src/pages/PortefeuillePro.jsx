import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Layout } from "@/components/Layout";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { GanttGrid, effectiveDates, startOfToday, addMonthsD, isoDate } from "@/components/GanttGrid";
import { List, GanttChartSquare, Building2, AlarmClock, Info } from "lucide-react";

const URGENCE_COLORS = { normal: "bg-blue-500", approaching: "bg-amber-400", critical: "bg-red-500" };
const DONE = new Set(["fait", "valide", "complete", "completee", "conforme", "termine", "certifie"]);

function PortfolioGantt({ dossiers, clientName, onOpen }) {
  const today = useMemo(startOfToday, []);
  const rows = useMemo(() => dossiers.map((d) => {
    const startStr = d.date_attestation_inscription || (d.created_at || "").slice(0, 10);
    const eff = effectiveDates({ debut: startStr, fin: d.echeance_module1 }, today, "debut", "fin");
    const client = d.client_id ? clientName(d.client_id) : "";
    return {
      code: d.id, badge: d.regime === "A" ? "PME" : (d.comite_requis ? "100+" : "25-99"),
      label: `${d.nom_entreprise}${client ? " · " + client : ""}`,
      statut: d.urgence_module1 || "normal",
      incontournable: d.urgence_module1 === "critical",
      planned: !!(startStr || d.echeance_module1), debut: eff.debut, echeance: eff.echeance,
    };
  }), [dossiers, today, clientName]);

  return (
    <div className="space-y-4" data-testid="portfolio-gantt">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-slate-500">
        <span className="font-semibold text-slate-600">Portefeuille — {rows.length} dossier(s), du début jusqu'à l'échéance légale</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-4 rounded bg-blue-500" /> {"> 30 j"}</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-4 rounded bg-amber-400" /> {"≤ 30 j"}</span>
        <span className="flex items-center gap-1"><span className="inline-block h-3 w-4 rounded ring-2 ring-red-500 bg-red-500" /> {"≤ 7 j (critique)"}</span>
        <span className="flex items-center gap-1"><span className="inline-block h-4 w-0.5 bg-red-500" /> aujourd'hui</span>
      </div>
      <GanttGrid rows={rows} statutColors={URGENCE_COLORS} onSelect={onOpen} testId="portfolio-gantt-grid" />
      <p className="text-[11px] text-slate-400">Une barre par dossier client, de la date d'attestation d'inscription jusqu'à l'échéance légale de l'analyse. Cliquez pour ouvrir le dossier.</p>
    </div>
  );
}

function PortfolioKanban({ dossiers, stages, clientName, onOpen }) {
  const cols = useMemo(() => (stages.length ? stages : [{ key: "inscription", label: "Inscription" }]), [stages]);
  const currentStageKey = (d) => {
    const st = d.stages || [];
    const ordered = [...st].sort((a, b) => (a.ordre || 0) - (b.ordre || 0));
    const pending = ordered.find((s) => !DONE.has(s.statut));
    return pending ? pending.key : (ordered[ordered.length - 1]?.key || cols[0].key);
  };
  const byCol = useMemo(() => {
    const map = {};
    cols.forEach((c) => (map[c.key] = []));
    dossiers.forEach((d) => {
      const k = currentStageKey(d);
      (map[k] = map[k] || []).push(d);
    });
    return map;
  }, [dossiers, cols]);

  return (
    <div className="space-y-3" data-testid="portfolio-kanban">
      <p className="text-[11px] text-slate-400">Colonnes = étapes du pipeline de francisation. Chaque dossier est placé à son étape courante. Cliquez une carte pour ouvrir le dossier.</p>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {cols.map((c) => (
          <div key={c.key} className="w-64 shrink-0" data-testid={`portfolio-col-${c.key}`}>
            <div className="rounded-t-lg bg-slate-100 border border-slate-200 px-3 py-2 flex items-center justify-between">
              <span className="text-xs font-semibold text-[#0F2B48]">{c.label}</span>
              <span className="text-[10px] bg-white text-slate-500 rounded-full px-1.5 py-0.5 border border-slate-200">{(byCol[c.key] || []).length}</span>
            </div>
            <div className="rounded-b-lg border border-t-0 border-slate-200 bg-slate-50 p-2 space-y-2 min-h-[80px]">
              {(byCol[c.key] || []).map((d) => (
                <button key={d.id} onClick={() => onOpen(d.id)} data-testid={`portfolio-card-${d.id}`}
                  className="w-full text-left rounded-lg bg-white border border-slate-200 p-2.5 hover:shadow-md hover:border-slate-300 transition-all">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[9px] font-semibold px-1 rounded bg-indigo-100 text-indigo-700">{d.comite_requis ? "100+" : "25-99"}</span>
                    <span className="text-xs font-bold text-[#0F2B48] truncate">{d.nom_entreprise}</span>
                  </div>
                  {d.client_id && <div className="text-[10px] text-slate-400 mt-0.5">{clientName(d.client_id)}</div>}
                  <div className={`text-[10px] mt-1 font-medium ${d.urgence_module1 === "critical" ? "text-red-600" : d.urgence_module1 === "approaching" ? "text-amber-600" : "text-slate-500"}`}>
                    {d.echeance_module1 ? `Analyse due le ${d.echeance_module1} · ${d.jours_restants_module1 < 0 ? `retard ${Math.abs(d.jours_restants_module1)} j` : `${d.jours_restants_module1} j`}` : "Échéance non définie"}
                  </div>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PortefeuillePro() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [view, setView] = useState("gantt");
  const [dossiers, setDossiers] = useState([]);
  const [clients, setClients] = useState([]);
  const [stages, setStages] = useState([]);

  useEffect(() => {
    Promise.all([api.get("/dossiers"), api.get("/clients"), api.get("/catalogue/stages")])
      .then(([d, c, s]) => { setDossiers(d.data); setClients(c.data); setStages(s.data); })
      .catch(() => {});
  }, []);

  const regimeB = useMemo(() => dossiers.filter((d) => d.regime !== "A"), [dossiers]);
  const clientName = (id) => clients.find((c) => c.id === id)?.nom || "";
  const open = (id) => navigate(`/dossier/${id}`);
  const critical = regimeB.filter((d) => d.urgence_module1 === "critical").length;

  return (
    <Layout>
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h1 className="font-display text-3xl font-extrabold text-[#0F2B48]">Portefeuille</h1>
          <p className="text-slate-500">Suivi d'ensemble de vos dossiers clients de francisation — comparez la vue chronologique (Gantt) et la vue par étape (Kanban).</p>
        </div>
        <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
          <button onClick={() => setView("gantt")} data-testid="portfolio-view-gantt"
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${view === "gantt" ? "bg-white shadow-sm text-[#0F2B48]" : "text-slate-500 hover:text-slate-700"}`}>
            <GanttChartSquare size={15} /> Gantt
          </button>
          <button onClick={() => setView("kanban")} data-testid="portfolio-view-kanban"
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${view === "kanban" ? "bg-white shadow-sm text-[#0F2B48]" : "text-slate-500 hover:text-slate-700"}`}>
            <List size={15} /> Kanban
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <Card className="p-4 flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center"><Building2 size={20} /></div>
          <div><div className="text-xl font-bold text-[#0F2B48]" data-testid="portfolio-count">{regimeB.length}</div><div className="text-xs text-slate-500">Dossiers de francisation</div></div>
        </Card>
        <Card className="p-4 flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-red-100 text-red-700 flex items-center justify-center"><AlarmClock size={20} /></div>
          <div><div className="text-xl font-bold text-[#0F2B48]">{critical}</div><div className="text-xs text-slate-500">Échéance critique (≤ 7 j)</div></div>
        </Card>
        <Card className="p-4 flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center"><Info size={20} /></div>
          <div><div className="text-xs text-slate-500 leading-snug">Maquette de suivi. Dites-moi laquelle des deux vues vous préférez comme vue principale du portefeuille.</div></div>
        </Card>
      </div>

      {regimeB.length === 0 ? (
        <Card className="p-12 text-center" data-testid="portfolio-empty">
          <Building2 className="mx-auto text-slate-300 mb-3" size={40} />
          <h3 className="font-display font-bold text-slate-700">Aucun dossier de francisation</h3>
          <p className="text-sm text-slate-500">Créez des dossiers clients (25+ employés) depuis le tableau de bord pour alimenter le portefeuille.</p>
        </Card>
      ) : view === "gantt"
        ? <PortfolioGantt dossiers={regimeB} clientName={clientName} onOpen={open} />
        : <PortfolioKanban dossiers={regimeB} stages={stages} clientName={clientName} onOpen={open} />}
    </Layout>
  );
}
