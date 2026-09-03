import { Badge } from "@/components/ui/badge";

const MAP = {
  a_faire: { label: "À faire", cls: "bg-slate-100 text-slate-600 border-slate-300" },
  en_cours: { label: "En cours", cls: "bg-blue-50 text-blue-700 border-blue-300" },
  soumis: { label: "Soumis à l'OQLF", cls: "bg-amber-100 text-amber-800 border-amber-300" },
  accepte: { label: "Accepté", cls: "bg-green-100 text-green-800 border-green-300" },
  refuse: { label: "Refusé / À corriger", cls: "bg-red-100 text-red-800 border-red-300" },
};

export function StatusBadge({ statut, testId }) {
  const s = MAP[statut] || MAP.a_faire;
  return (
    <Badge variant="outline" data-testid={testId} className={`font-medium ${s.cls}`}>
      {s.label}
    </Badge>
  );
}

export const STATUT_OPTIONS = Object.entries(MAP).map(([value, v]) => ({ value, label: v.label }));
