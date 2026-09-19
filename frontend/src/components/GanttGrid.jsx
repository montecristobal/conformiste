import { useMemo } from "react";
import { AlertTriangle } from "lucide-react";

export const DAY = 86400000;
export const isoDate = (d) => d.toISOString().slice(0, 10);
export const parseDate = (s) => (s ? new Date(s + "T00:00:00") : null);
export const startOfToday = () => { const t = new Date(); t.setHours(0, 0, 0, 0); return t; };
export const mondayOf = (d) => { const x = new Date(d); const day = (x.getDay() + 6) % 7; x.setDate(x.getDate() - day); x.setHours(0, 0, 0, 0); return x; };
export const addDaysD = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
export const addMonthsD = (d, n) => { const x = new Date(d); x.setMonth(x.getMonth() + n); return x; };

// Dates effectives : défaut aujourd'hui → +3 mois si non planifié
export function effectiveDates(saved, today, startKey = "date_debut", endKey = "date_echeance") {
  const planned = !!(saved?.[startKey] || saved?.[endKey]);
  const debut = parseDate(saved?.[startKey]) || today;
  const echeance = parseDate(saved?.[endKey]) || addMonthsD(debut, 3);
  return { planned, debut, echeance };
}

// Diagramme de Gantt générique.
// rows: [{ code, label, statut, incontournable, planned, debut(Date), echeance(Date) }]
export function GanttGrid({ rows, statutColors = {}, onSelect, testId = "gantt-grid", colW = 64 }) {
  const today = useMemo(startOfToday, []);

  const { start, end, weeks } = useMemo(() => {
    if (!rows.length) return { start: today, end: addMonthsD(today, 3), weeks: [] };
    let mn = today, mx = addMonthsD(today, 3);
    rows.forEach((r) => { if (r.debut < mn) mn = r.debut; if (r.echeance > mx) mx = r.echeance; });
    const s = mondayOf(mn);
    const e = addDaysD(mondayOf(mx), 7);
    const w = [];
    for (let cur = new Date(s); cur < e; cur = addDaysD(cur, 7)) w.push(new Date(cur));
    return { start: s, end: e, weeks: w };
  }, [rows, today]);

  const totalDays = Math.max(1, (end - start) / DAY);
  const pct = (d) => ((d - start) / DAY / totalDays) * 100;
  const todayPct = pct(today);
  const gridW = weeks.length * colW;

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-x-auto" data-testid={testId}>
      <div className="flex" style={{ minWidth: 240 + gridW }}>
        <div className="w-60 shrink-0 border-r border-slate-200">
          <div className="h-9 border-b border-slate-200 bg-slate-50 flex items-center px-3 text-[11px] font-semibold text-slate-500">Élément</div>
          {rows.map((r) => (
            <button key={r.code} onClick={() => onSelect(r.code)} data-testid={`${testId}-label-${r.code}`}
              className="h-10 w-full border-b border-slate-100 flex items-center gap-2 px-3 text-left hover:bg-indigo-50">
              {r.badge && <span className="text-[10px] font-mono font-semibold px-1 rounded bg-indigo-100 text-indigo-700 shrink-0">{r.badge}</span>}
              <span className="text-xs text-[#0F2B48] truncate">{r.label}</span>
            </button>
          ))}
        </div>
        <div className="relative" style={{ width: gridW }}>
          <div className="h-9 border-b border-slate-200 bg-slate-50 flex">
            {weeks.map((w, i) => (
              <div key={i} className="border-r border-slate-100 flex flex-col items-center justify-center text-[9px] text-slate-400 leading-none" style={{ width: colW }}>
                <span className="font-semibold text-slate-500">{w.toLocaleDateString("fr-CA", { day: "2-digit", month: "2-digit" })}</span>
                <span>sem.</span>
              </div>
            ))}
          </div>
          <div className="relative">
            <div className="absolute inset-0 flex pointer-events-none">
              {weeks.map((_, i) => <div key={i} className="border-r border-slate-100" style={{ width: colW }} />)}
            </div>
            {todayPct >= 0 && todayPct <= 100 && (
              <div className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10" style={{ left: `${todayPct}%` }} data-testid={`${testId}-today-line`} />
            )}
            {rows.map((r) => {
              const left = pct(r.debut);
              const width = Math.max(1.5, pct(r.echeance) - left);
              const barCls = r.incontournable ? "bg-red-500 ring-2 ring-red-600" : (statutColors[r.statut] || "bg-indigo-500");
              return (
                <div key={r.code} className="h-10 border-b border-slate-100 relative">
                  <button onClick={() => onSelect(r.code)} data-testid={`${testId}-bar-${r.code}`}
                    title={`${r.label} — ${isoDate(r.debut)} → ${isoDate(r.echeance)}`}
                    className={`absolute top-1.5 h-7 rounded-md ${barCls} ${!r.planned ? "opacity-60 border-2 border-dashed border-slate-400" : ""} hover:brightness-110 transition-all flex items-center px-1.5`}
                    style={{ left: `${left}%`, width: `${width}%`, minWidth: 18 }}>
                    {r.incontournable && <AlertTriangle size={11} className="text-white shrink-0" />}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
