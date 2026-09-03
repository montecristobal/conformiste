import { Check, Lock } from "lucide-react";

const STATUT_DOT = {
  a_faire: "bg-slate-300",
  en_cours: "bg-blue-500",
  soumis: "bg-amber-500",
  accepte: "bg-green-500",
  refuse: "bg-red-500",
};

export function PipelineStepper({ stages, activeKey, onSelect }) {
  return (
    <div className="overflow-x-auto pb-2" data-testid="pipeline-stepper">
      <div className="flex items-stretch gap-0 min-w-max">
        {stages.map((s, i) => {
          const active = s.key === activeKey;
          const done = s.statut === "accepte";
          return (
            <button
              key={s.key}
              data-testid={`pipeline-stage-node-${s.ordre}`}
              onClick={() => onSelect?.(s.key)}
              className={`group relative flex flex-col items-center px-4 py-3 min-w-[130px] transition-colors ${
                active ? "bg-[#0F2B48] text-white" : "bg-white hover:bg-slate-50 text-slate-700"
              } ${i === 0 ? "rounded-l-xl" : ""} ${i === stages.length - 1 ? "rounded-r-xl" : ""} border border-slate-200 ${i > 0 ? "-ml-px" : ""}`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                  active ? "bg-white text-[#0F2B48]" : done ? "bg-green-500 text-white" : "bg-slate-100 text-slate-600"
                }`}>
                  {done ? <Check size={14} /> : s.ordre}
                </span>
                <span className={`h-2 w-2 rounded-full ${STATUT_DOT[s.statut] || "bg-slate-300"}`} />
              </div>
              <span className="text-[11px] leading-tight text-center font-medium">{s.label}</span>
              {s.module && (
                <span className={`mt-1 text-[9px] uppercase tracking-wider ${active ? "text-blue-200" : "text-blue-500"}`}>
                  Module {s.module}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
