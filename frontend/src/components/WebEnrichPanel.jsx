import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Check, X, Sparkles, Globe, AlertTriangle, Image as ImageIcon } from "lucide-react";

export function WebEnrichPanel({ proposals, meta, onApply, onClose, onViewProof }) {
  const [accepted, setAccepted] = useState(() =>
    Object.fromEntries(proposals.map((_, i) => [i, true]))
  );
  const [zoom, setZoom] = useState(null);
  const toggle = (i, v) => setAccepted((a) => ({ ...a, [i]: v }));
  const setAll = (v) => setAccepted(Object.fromEntries(proposals.map((_, i) => [i, v])));
  const count = Object.values(accepted).filter(Boolean).length;

  const apply = () => {
    const map = {};
    proposals.forEach((p, i) => { if (accepted[i]) map[p.key] = p.value; });
    onApply(map);
  };

  return (
    <Card className="p-5 border-emerald-200 bg-emerald-50/40 space-y-4" data-testid="web-enrich-panel">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-emerald-700" />
          <div>
            <h4 className="font-display font-bold text-[#0F2B48]">Propositions issues de la recherche Web</h4>
            <p className="text-xs text-slate-500">Acceptez ou refusez chaque proposition. Seuls les champs acceptés seront pré-remplis.</p>
          </div>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600" data-testid="enrich-close" aria-label="Fermer">
          <X size={18} />
        </button>
      </div>

      {(meta?.site_used?.length > 0) && (
        <div className="flex items-center gap-1.5 text-xs text-emerald-800" data-testid="enrich-sites">
          <Globe size={13} /> Sources analysées : {meta.site_used.join(", ")}
        </div>
      )}
      {(meta?.warnings || []).map((w, i) => (
        <div key={i} className="flex items-center gap-1.5 text-xs text-amber-700" data-testid={`enrich-warning-${i}`}>
          <AlertTriangle size={13} /> {w}
        </div>
      ))}

      {(meta?.evidence || []).length > 0 && (
        <div className="space-y-2" data-testid="enrich-evidence">
          <p className="text-xs font-semibold text-slate-700">Preuves jointes au dossier (captures d'écran horodatées)</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {meta.evidence.map((e, i) => (
              <div key={i} data-testid={`evidence-${i}`} className="rounded-lg border border-slate-200 bg-white p-2 text-xs">
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  <span className={`rounded-full px-2 py-0.5 font-semibold ${e.is_french === true ? "bg-emerald-100 text-emerald-700" : e.is_french === false ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-500"}`}>
                    {e.is_french === true ? "Français" : e.is_french === false ? "Autre langue" : "Indéterminé"}
                  </span>
                  <span className="text-slate-500">{e.kind === "site" ? "Site Web" : "Média social"}</span>
                  {typeof e.confidence === "number" && <span className="text-slate-400">({Math.round(e.confidence * 100)}%)</span>}
                </div>
                <p className="truncate text-slate-600 mb-1.5" title={e.url}>{e.url}</p>
                {e.thumbUrl ? (
                  <img src={e.thumbUrl} alt={`Capture ${e.url}`} data-testid={`evidence-thumb-${i}`}
                    onClick={() => setZoom(e.thumbUrl)}
                    className="w-full h-44 object-cover object-top rounded border border-slate-200 cursor-zoom-in hover:opacity-90 transition-opacity" />
                ) : e.document_id ? (
                  <button onClick={() => onViewProof?.(e.document_id)} data-testid={`evidence-view-${i}`}
                    className="flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-slate-600 hover:bg-slate-200">
                    <ImageIcon size={12} /> Voir la capture
                  </button>
                ) : (
                  <span className="text-slate-400">Capture indisponible</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {proposals.length === 0 ? (
        <p className="text-sm text-slate-500" data-testid="enrich-empty">Aucune proposition n'a pu être établie à partir des sources disponibles.</p>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => setAll(true)} data-testid="enrich-accept-all">Tout accepter</Button>
            <Button size="sm" variant="outline" onClick={() => setAll(false)} data-testid="enrich-refuse-all">Tout refuser</Button>
          </div>
          <div className="space-y-2">
            {proposals.map((p, i) => (
              <div key={p.key} data-testid={`enrich-proposal-${i}`}
                className={`rounded-lg border p-3 transition-colors ${accepted[i] ? "border-emerald-300 bg-white" : "border-slate-200 bg-slate-50 opacity-70"}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-700">{p.label}</p>
                    <p className="text-sm text-[#0F2B48] font-medium break-words" data-testid={`enrich-value-${i}`}>{p.value}</p>
                    <div className="flex flex-wrap items-center gap-2 mt-1">
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-500">Source : {p.source}</span>
                      {typeof p.confidence === "number" && (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-500">Confiance : {Math.round(p.confidence * 100)}%</span>
                      )}
                      {p.note && <span className="text-[10px] text-slate-400 italic">{p.note}</span>}
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <button onClick={() => toggle(i, true)} data-testid={`enrich-accept-${i}`}
                      className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ${accepted[i] ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-500 hover:bg-emerald-50"}`}>
                      <Check size={13} /> Accepter
                    </button>
                    <button onClick={() => toggle(i, false)} data-testid={`enrich-refuse-${i}`}
                      className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ${!accepted[i] ? "bg-slate-600 text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"}`}>
                      <X size={13} /> Refuser
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-end">
            <Button size="sm" onClick={apply} disabled={count === 0} data-testid="enrich-apply" className="bg-[#0F2B48] hover:bg-[#0F2B48]/90">
              Appliquer {count} proposition{count > 1 ? "s" : ""} acceptée{count > 1 ? "s" : ""}
            </Button>
          </div>
        </>
      )}

      {zoom && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4" data-testid="evidence-zoom" onClick={() => setZoom(null)}>
          <img src={zoom} alt="Capture agrandie" className="max-h-[92vh] max-w-[92vw] rounded shadow-2xl" />
        </div>
      )}
    </Card>
  );
}
