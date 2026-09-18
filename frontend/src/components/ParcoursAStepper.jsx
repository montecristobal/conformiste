import { Check, Lock, Clock } from "lucide-react";

export const ParcoursAStepper = ({ dossier, active, onSelect }) => {
  const reqRequise = !!dossier.req_declaration_requise;
  const reqFaite = !!dossier.req_declaration;
  const steps = [
    { key: "conformite", num: 1, label: "Obligations universelles", sub: "U1 à U18" },
    {
      key: "req", num: 2, label: "Déclaration au REQ",
      sub: reqRequise ? (reqFaite ? "Enregistrée" : "Requise (≥ 5 employés)") : "Non applicable (< 5 employés)",
      done: reqRequise && reqFaite,
      muted: !reqRequise,
    },
    { key: "plainte", num: 3, label: "Traitement d'une plainte", sub: "À venir", disabled: true },
  ];

  return (
    <div className="flex items-stretch gap-2 overflow-x-auto" data-testid="parcours-a-stepper">
      {steps.map((s, i) => {
        const isActive = active === s.key;
        const clickable = !s.disabled;
        return (
          <button
            key={s.key}
            data-testid={`parcours-a-step-${s.key}`}
            disabled={s.disabled}
            onClick={() => clickable && onSelect(s.key)}
            className={`flex-1 min-w-[180px] text-left rounded-xl border-2 px-4 py-3 transition-all duration-200 ${
              s.disabled
                ? "border-slate-100 bg-slate-50/60 cursor-not-allowed"
                : isActive
                ? "border-indigo-500 bg-indigo-50/70 ring-4 ring-indigo-500/10"
                : "border-slate-200 bg-white hover:border-indigo-300"
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold ${
                s.done ? "bg-emerald-500 text-white"
                : s.disabled ? "bg-slate-200 text-slate-400"
                : isActive ? "bg-indigo-600 text-white" : "bg-slate-200 text-slate-600"
              }`}>
                {s.done ? <Check size={13} /> : s.disabled ? <Clock size={12} /> : s.num}
              </span>
              <span className={`text-sm font-semibold ${s.disabled ? "text-slate-400" : "text-[#0F2B48]"}`}>{s.label}</span>
              {s.muted && !s.disabled && <Lock size={12} className="text-slate-300 ml-auto" />}
            </div>
            <p className={`text-[11px] ${s.disabled ? "text-slate-400" : "text-slate-500"}`}>{s.sub}</p>
          </button>
        );
      })}
    </div>
  );
};
