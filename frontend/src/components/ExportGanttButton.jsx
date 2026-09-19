import { useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { FileDown, Image, Loader2 } from "lucide-react";

export const ExportGanttButton = ({ dossierId, kind }) => {
  const [busy, setBusy] = useState("");

  const download = async (format) => {
    setBusy(format);
    try {
      const { data } = await api.get(`/dossiers/${dossierId}/gantt/export?kind=${kind}&format=${format}`,
        { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `gantt_${kind}.${format}`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success(`Gantt exporté (${format.toUpperCase()})`);
    } catch (e) { toast.error("Échec de l'export"); } finally { setBusy(""); }
  };

  return (
    <div className="flex items-center gap-1.5">
      <Button size="sm" variant="outline" onClick={() => download("pdf")} disabled={!!busy} data-testid="gantt-export-pdf">
        {busy === "pdf" ? <Loader2 size={14} className="mr-1 animate-spin" /> : <FileDown size={14} className="mr-1" />} PDF
      </Button>
      <Button size="sm" variant="outline" onClick={() => download("png")} disabled={!!busy} data-testid="gantt-export-png">
        {busy === "png" ? <Loader2 size={14} className="mr-1 animate-spin" /> : <Image size={14} className="mr-1" />} PNG
      </Button>
    </div>
  );
};
