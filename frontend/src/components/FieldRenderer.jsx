import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2, Paperclip, Upload, Loader2 } from "lucide-react";
import api, { openDocument } from "@/lib/api";
import { toast } from "sonner";

function FileUploadField({ tid, value, onChange, dossierId }) {
  const [busy, setBusy] = useState(false);
  const v = value && typeof value === "object" ? value : null;
  const up = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post(`/dossiers/${dossierId}/documents`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      onChange({ document_id: data.id, filename: data.original_filename });
      toast.success("Document joint");
    } catch (err) { toast.error("Échec du téléversement"); }
    finally { setBusy(false); e.target.value = ""; }
  };
  return (
    <div className="flex items-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-2">
      {v ? (
        <>
          <Paperclip size={15} className="text-emerald-500 shrink-0" />
          <button type="button" className="text-sm text-blue-600 hover:underline truncate" onClick={() => openDocument(v.document_id)} data-testid={`${tid}-view`}>{v.filename}</button>
          <Button type="button" variant="ghost" size="icon" className="h-7 w-7 ml-auto text-red-500" onClick={() => onChange("")} data-testid={`${tid}-remove`}><Trash2 size={14} /></Button>
        </>
      ) : typeof value === "string" && value ? (
        <>
          <Paperclip size={15} className="text-slate-400 shrink-0" />
          <span className="text-sm text-slate-600 truncate">{value}</span>
          <Button type="button" variant="ghost" size="icon" className="h-7 w-7 ml-auto text-red-500" onClick={() => onChange("")}><Trash2 size={14} /></Button>
        </>
      ) : (
        <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-500 w-full" data-testid={`${tid}-label`}>
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} className="text-slate-400" />}
          {busy ? "Téléversement…" : "Téléverser un document (PDF, image)"}
          <input type="file" accept=".pdf,image/png,image/jpeg,image/webp" className="hidden" onChange={up} disabled={busy || !dossierId} data-testid={tid} />
        </label>
      )}
    </div>
  );
}

function shouldShow(field, values, sectionId) {
  if (!field.showIf) return true;
  const key = `${sectionId}.${field.showIf.field}`;
  return field.showIf.in.includes(values[key]);
}

export function FieldRenderer({ field, sectionId, values, onChange, dossierId }) {
  if (!shouldShow(field, values, sectionId)) return null;
  const key = `${sectionId}.${field.id}`;
  const val = values[key];
  const set = (v) => onChange(key, v);
  const tid = `m1-${key.replace(/\./g, "-")}`;

  const labelEl = (
    <Label className="text-sm font-medium text-slate-700">
      {field.label}{field.required && <span className="text-red-500"> *</span>}
    </Label>
  );

  if (field.type === "text" || field.type === "percent" || field.type === "number" || field.type === "date") {
    const type = field.type === "date" ? "date" : field.type === "text" ? "text" : "number";
    return (
      <div className="space-y-1.5">
        {labelEl}
        <Input type={type} data-testid={tid} value={val ?? ""}
          onChange={(e) => set(field.type === "text" || field.type === "date" ? e.target.value : e.target.value === "" ? "" : Number(e.target.value))}
          placeholder={field.type === "percent" ? "0 – 100 %" : ""} />
      </div>
    );
  }

  if (field.type === "textarea") {
    return (
      <div className="space-y-1.5">
        {labelEl}
        <Textarea data-testid={tid} value={val ?? ""} onChange={(e) => set(e.target.value)} rows={3} />
      </div>
    );
  }

  if (field.type === "radio") {
    return (
      <div className="space-y-2">
        {labelEl}
        <RadioGroup value={val ?? ""} onValueChange={set} className="flex flex-wrap gap-4" data-testid={tid}>
          {field.options.map((o) => (
            <div key={o} className="flex items-center gap-2">
              <RadioGroupItem value={o} id={`${tid}-${o}`} data-testid={`${tid}-opt-${o}`} />
              <Label htmlFor={`${tid}-${o}`} className="text-sm font-normal cursor-pointer">{o}</Label>
            </div>
          ))}
        </RadioGroup>
      </div>
    );
  }

  if (field.type === "select") {
    return (
      <div className="space-y-1.5">
        {labelEl}
        <Select value={val ?? ""} onValueChange={set}>
          <SelectTrigger data-testid={tid}><SelectValue placeholder="Sélectionner…" /></SelectTrigger>
          <SelectContent className="bg-white">
            {field.options.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
    );
  }

  if (field.type === "multicheck") {
    const arr = Array.isArray(val) ? val : [];
    const toggle = (o) => set(arr.includes(o) ? arr.filter((x) => x !== o) : [...arr, o]);
    return (
      <div className="space-y-2">
        {labelEl}
        <div className="flex flex-col gap-2">
          {field.options.map((o) => (
            <div key={o} className="flex items-center gap-2">
              <Checkbox id={`${tid}-${o}`} checked={arr.includes(o)} onCheckedChange={() => toggle(o)} data-testid={`${tid}-opt-${o}`} />
              <Label htmlFor={`${tid}-${o}`} className="text-sm font-normal cursor-pointer">{o}</Label>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (field.type === "file") {
    return (
      <div className="space-y-1.5">
        {labelEl}
        <FileUploadField tid={tid} value={val} onChange={set} dossierId={dossierId} />
      </div>
    );
  }

  if (field.type === "table") {
    const rows = Array.isArray(val) ? val : [];
    const addRow = () => set([...rows, {}]);
    const removeRow = (i) => set(rows.filter((_, idx) => idx !== i));
    const setCell = (i, cid, v) => set(rows.map((r, idx) => (idx === i ? { ...r, [cid]: v } : r)));
    return (
      <div className="space-y-2 md:col-span-2">
        {labelEl}
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {field.columns.map((c) => <th key={c.id} className="text-left px-3 py-2 font-medium text-slate-600 text-xs">{c.label}</th>)}
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={field.columns.length + 1} className="px-3 py-4 text-center text-slate-400 text-sm">Aucune ligne</td></tr>
              )}
              {rows.map((r, i) => (
                <tr key={i} className="border-t border-slate-100">
                  {field.columns.map((c) => (
                    <td key={c.id} className="px-2 py-1.5">
                      {c.type === "select" ? (
                        <Select value={r[c.id] ?? ""} onValueChange={(v) => setCell(i, c.id, v)}>
                          <SelectTrigger data-testid={`${tid}-row-${i}-${c.id}`} className="h-9 text-xs"><SelectValue placeholder="…" /></SelectTrigger>
                          <SelectContent className="bg-white">
                            {c.options.map((o) => <SelectItem key={o} value={o} className="text-xs">{o}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      ) : (
                        <Input type={c.type === "number" ? "number" : "text"} value={r[c.id] ?? ""}
                          data-testid={`${tid}-row-${i}-${c.id}`}
                          onChange={(e) => setCell(i, c.id, c.type === "number" ? (e.target.value === "" ? "" : Number(e.target.value)) : e.target.value)}
                          className="h-9 text-xs" />
                      )}
                    </td>
                  ))}
                  <td className="px-2">
                    <Button type="button" variant="ghost" size="icon" onClick={() => removeRow(i)}
                      data-testid={`${tid}-remove-row-${i}`} className="h-8 w-8 text-red-500 hover:text-red-600">
                      <Trash2 size={15} />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={addRow} data-testid={`${tid}-add-row`}>
          <Plus size={15} className="mr-1" /> Ajouter une ligne
        </Button>
      </div>
    );
  }

  return null;
}
