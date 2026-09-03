import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileDown, ShieldCheck, User } from "lucide-react";

export function AuditLog({ dossierId }) {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    api.get(`/dossiers/${dossierId}/audit`).then(({ data }) => setRows(data)).catch(() => {});
  }, [dossierId]);

  const exportCsv = () => {
    const header = "Horodatage,Acteur,Mode,Action,Détails,Empreinte\n";
    const body = rows.map((r) => `"${r.timestamp}","${r.actor_email}","${r.mode}","${r.action}","${r.details}","${r.checksum}"`).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `journal_audit_${dossierId}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card className="p-6" data-testid="audit-log">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-display text-lg font-bold text-[#0F2B48]">Journal d'audit</h3>
          <p className="text-xs text-slate-500">Horodaté et immuable — chaque modification et export est consigné.</p>
        </div>
        <Button variant="outline" size="sm" onClick={exportCsv} data-testid="audit-log-export-button">
          <FileDown size={15} className="mr-1" /> Exporter CSV
        </Button>
      </div>
      <div className="relative pl-5">
        <div className="absolute left-[7px] top-1 bottom-1 w-px bg-slate-200" />
        {rows.length === 0 && <p className="text-sm text-slate-400">Aucune entrée pour le moment.</p>}
        <div className="space-y-4">
          {rows.map((r) => (
            <div key={r.id} className="relative" data-testid={`audit-entry-${r.id}`}>
              <span className="absolute -left-[13px] top-1 h-3 w-3 rounded-full bg-[#2563EB] ring-4 ring-blue-100" />
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="text-sm font-medium text-slate-800">{r.action}</span>
                {r.details && <span className="text-xs text-slate-500">— {r.details}</span>}
              </div>
              <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 mt-0.5">
                <span>{new Date(r.timestamp).toLocaleString("fr-CA")}</span>
                <span className="flex items-center gap-1"><User size={11} /> {r.actor_email}</span>
                <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">{r.mode}</span>
                <span className="flex items-center gap-1 font-mono"><ShieldCheck size={11} /> {r.checksum}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
