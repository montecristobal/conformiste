import { useEffect, useRef, useState } from "react";
import api, { downloadPdf } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Building2, RefreshCw, Loader2, Send, FileDown, ClipboardList, CircleHelp } from "lucide-react";

const YESNO = ["Oui", "Non"];
const PRISE_OPTS = [
  "Site Internet de l'Office",
  "Demande d'inscription transmise par l'Office",
  "Médias sociaux de l'Office (Facebook, X, etc.)",
  "Dépliants d'information numériques",
  "Dépliants d'information papiers",
  "Regroupement d'entreprises ou autres associations",
  "Exigence dans un appel d'offres public ou une demande de subvention",
  "Autres",
];
const GERE_OPTS = ["Oui", "Non ou en partie seulement"];

// source: "req" (pré-rempli depuis le Registraire) | "entrevue" (à compléter) | null
const SECTIONS = [
  {
    titre: "Informations générales",
    fields: [
      { k: "prise_connaissance", label: "Comment avez-vous pris connaissance de l'obligation de vous inscrire ?", type: "select", options: PRISE_OPTS, source: "entrevue" },
      { k: "prise_connaissance_autre", label: "Autres (précisez)", type: "text", source: "entrevue", showIf: (d) => d.prise_connaissance === "Autres" },
    ],
  },
  {
    titre: "1. Identité de l'entreprise",
    fields: [
      { k: "nom_entreprise", label: "Nom de l'entreprise (immatriculé au registre du Québec)", type: "text", source: "req" },
      { k: "neq", label: "Numéro d'entreprise du Québec (NEQ)", type: "text", source: "req" },
      { k: "autres_noms", label: "Autres noms utilisés au Québec", type: "text", source: "req" },
      { k: "site_web", label: "Site Web", type: "text", source: "entrevue" },
      { k: "etab_principal_adresse", label: "Principal établissement — numéro, rue, local", type: "text", source: "req", full: true },
      { k: "etab_principal_ville_cp", label: "Ville et code postal", type: "text", source: "req" },
    ],
  },
  {
    titre: "2. Responsable de la direction au Québec",
    fields: [
      { k: "resp_civilite", label: "Civilité", type: "select", options: ["Madame", "Monsieur"], source: "entrevue" },
      { k: "resp_prenom", label: "Prénom", type: "text", source: "req" },
      { k: "resp_nom", label: "Nom", type: "text", source: "req" },
      { k: "resp_titre", label: "Titre ou fonction", type: "text", source: "req" },
      { k: "resp_courriel", label: "Courriel", type: "text", source: "entrevue" },
      { k: "resp_telephone", label: "Téléphone", type: "text", source: "entrevue" },
      { k: "resp_poste", label: "Poste", type: "text", source: "entrevue" },
      { k: "resp_telecopieur", label: "Télécopieur", type: "text", source: "entrevue" },
      { k: "resp_adresse", label: "Adresse — numéro, rue, local", type: "text", source: "entrevue", full: true },
      { k: "resp_ville_cp", label: "Ville et code postal", type: "text", source: "entrevue" },
    ],
  },
  {
    titre: "3. Personne-ressource auprès de l'Office (si différente)",
    fields: [
      { k: "pr_differente", label: "Une personne-ressource différente du responsable ?", type: "select", options: YESNO, source: "entrevue" },
      { k: "pr_civilite", label: "Civilité", type: "select", options: ["Madame", "Monsieur"], source: "entrevue", showIf: (d) => d.pr_differente === "Oui" },
      { k: "pr_prenom", label: "Prénom", type: "text", source: "entrevue", showIf: (d) => d.pr_differente === "Oui" },
      { k: "pr_nom", label: "Nom", type: "text", source: "entrevue", showIf: (d) => d.pr_differente === "Oui" },
      { k: "pr_titre", label: "Titre ou fonction", type: "text", source: "entrevue", showIf: (d) => d.pr_differente === "Oui" },
      { k: "pr_courriel", label: "Courriel", type: "text", source: "entrevue", showIf: (d) => d.pr_differente === "Oui" },
      { k: "pr_telephone", label: "Téléphone", type: "text", source: "entrevue", showIf: (d) => d.pr_differente === "Oui" },
      { k: "pr_poste", label: "Poste", type: "text", source: "entrevue", showIf: (d) => d.pr_differente === "Oui" },
      { k: "pr_telecopieur", label: "Télécopieur", type: "text", source: "entrevue", showIf: (d) => d.pr_differente === "Oui" },
      { k: "pr_adresse", label: "Adresse — numéro, rue, local", type: "text", source: "entrevue", full: true, showIf: (d) => d.pr_differente === "Oui" },
      { k: "pr_ville_cp", label: "Ville et code postal", type: "text", source: "entrevue", showIf: (d) => d.pr_differente === "Oui" },
    ],
  },
  {
    titre: "4. Activités commerciales au Québec",
    fields: [
      { k: "activites_principales", label: "4.1 Principales activités de l'entreprise", type: "textarea", source: "req", full: true },
      { k: "activites_economiques", label: "4.2 Activités économiques (telles qu'au REQ)", type: "textarea", source: "req", full: true },
      { k: "codes_cae", label: "Codes d'activités économiques (CAE)", type: "text", source: "req" },
    ],
  },
  {
    titre: "5. Structure de l'entreprise au Québec",
    fields: [
      { k: "deja_50_plus", label: "5.1 A déjà employé 50 personnes ou plus durant 6 mois au Québec ?", type: "select", options: YESNO, source: "entrevue", full: true },
      { k: "nb_employes_actuel", label: "5.2 Nombre de personnes employées actuellement (tous statuts)", type: "number", source: "entrevue" },
      { k: "nb_etablissements", label: "5.3 Nombre d'établissements au Québec", type: "number", source: "req" },
      { k: "etablissements_villes", label: "5.3 Ville(s) où ils sont situés", type: "textarea", source: "req", full: true },
      { k: "siege_au_quebec", label: "5.4 Le siège social est-il au Québec ?", type: "select", options: YESNO, source: "entrevue" },
      { k: "siege_lieu", label: "5.4 Si non, lieu (ville et pays)", type: "text", source: "entrevue", showIf: (d) => d.siege_au_quebec === "Non" },
      { k: "gere_admin", label: "5.5 Gère-t-elle elle-même ses fonctions administratives au Québec ?", type: "select", options: GERE_OPTS, source: "entrevue" },
      { k: "gere_admin_precision", label: "5.5 Si non ou en partie, expliquez", type: "textarea", source: "entrevue", full: true, showIf: (d) => d.gere_admin && d.gere_admin !== "Oui" },
      { k: "centre_recherche", label: "5.6 A-t-elle un centre de recherche au Québec ?", type: "select", options: YESNO, source: "entrevue" },
      { k: "centre_recherche_domaines", label: "5.6 Si oui, domaines de recherche", type: "text", source: "entrevue", showIf: (d) => d.centre_recherche === "Oui" },
      { k: "etab_hors_quebec", label: "5.7 Possède-t-elle des établissements hors Québec ?", type: "select", options: YESNO, source: "entrevue" },
    ],
  },
  {
    titre: "6. Attestation du responsable de la direction",
    fields: [
      { k: "att_prenom", label: "Prénom", type: "text", source: "req" },
      { k: "att_nom", label: "Nom", type: "text", source: "req" },
      { k: "att_titre", label: "Titre ou fonction", type: "text", source: "req" },
      { k: "att_date", label: "Date de l'attestation", type: "date", source: "entrevue" },
    ],
  },
];

const ALL_FIELDS = SECTIONS.flatMap((s) => s.fields);

function isEmpty(v) {
  return v === undefined || v === null || v === "";
}

function mapReqToOqlf(req, current) {
  const acts = req.activites_economiques || [];
  const chef = (req.administrateurs || [])[0] || {};
  const parts = (chef.nom || "").trim().split(/\s+/);
  const prenom = parts.length > 1 ? parts.slice(0, -1).join(" ") : (parts[0] || "");
  const nom = parts.length > 1 ? parts[parts.length - 1] : "";
  const etabPrincipal = (req.etablissements || []).find((e) => e.principal) || (req.etablissements || [])[0] || {};
  const today = new Date().toISOString().slice(0, 10);
  return {
    ...current,
    _req: req,
    nom_entreprise: req.nom_entreprise ?? current.nom_entreprise ?? "",
    neq: req.neq ?? current.neq ?? "",
    autres_noms: (req.autres_noms || []).join(", "),
    etab_principal_adresse: etabPrincipal.adresse || req.adresse_domicile || "",
    etab_principal_ville_cp: [req.ville, req.code_postal].filter(Boolean).join(", "),
    resp_prenom: prenom,
    resp_nom: nom,
    resp_titre: chef.fonction || "",
    activites_principales: acts.map((a) => a.description).join(" ; "),
    activites_economiques: acts.map((a) => a.description).join(" ; "),
    codes_cae: acts.map((a) => a.code_cae).join(", "),
    nb_etablissements: req.nombre_etablissements ?? current.nb_etablissements ?? "",
    etablissements_villes: (req.etablissements || []).map((e) => `${e.nom}${e.principal ? " (principal)" : ""} — ${e.adresse}`).join("\n"),
    nb_employes_actuel: current.nb_employes_actuel ?? req.nombre_employes_estime ?? "",
    att_prenom: prenom,
    att_nom: nom,
    att_titre: chef.fonction || "",
    att_date: current.att_date || today,
  };
}

function OqlfField({ field, d, set }) {
  const { k, label, type, options, source, full } = field;
  const empty = isEmpty(d[k]);
  const highlight = source === "entrevue" && empty;
  return (
    <div className={`space-y-1.5 ${full ? "sm:col-span-2" : ""}`}>
      <Label className="text-xs flex items-center gap-1.5">
        {label}
        {source === "req" && (
          <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-700">REQ</span>
        )}
        {highlight && (
          <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[9px] font-semibold text-amber-700">à compléter</span>
        )}
      </Label>
      {type === "select" ? (
        <Select value={d[k] ?? ""} onValueChange={(v) => set(k, v)}>
          <SelectTrigger data-testid={`oqlf-${k}`} className={highlight ? "border-amber-300 bg-amber-50/40" : ""}>
            <SelectValue placeholder="Sélectionner…" />
          </SelectTrigger>
          <SelectContent className="bg-white">
            {options.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
          </SelectContent>
        </Select>
      ) : type === "textarea" ? (
        <Textarea rows={2} value={d[k] ?? ""} data-testid={`oqlf-${k}`}
          className={highlight ? "border-amber-300 bg-amber-50/40" : ""}
          onChange={(e) => set(k, e.target.value)} />
      ) : (
        <Input type={type === "number" ? "number" : type === "date" ? "date" : "text"}
          value={d[k] ?? ""} data-testid={`oqlf-${k}`}
          className={highlight ? "border-amber-300 bg-amber-50/40" : ""}
          onChange={(e) => set(k, type === "number" ? (e.target.value === "" ? "" : Number(e.target.value)) : e.target.value)} />
      )}
    </div>
  );
}

function ReqPanel({ req }) {
  if (!req) return null;
  const Row = ({ label, value }) => (
    <div className="flex gap-2 py-0.5">
      <span className="w-44 shrink-0 text-slate-500">{label}</span>
      <span className="text-slate-800 font-medium">{value || "—"}</span>
    </div>
  );
  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4 text-xs space-y-1" data-testid="req-panel">
      <div className="flex items-center gap-2 mb-2">
        <Building2 size={15} className="text-emerald-700" />
        <span className="font-semibold text-emerald-800">Données récupérées au Registraire des entreprises</span>
        <span className="ml-auto rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">Démo</span>
      </div>
      <Row label="Dénomination" value={req.nom_entreprise} />
      <Row label="Forme juridique" value={req.forme_juridique} />
      <Row label="Statut / état" value={`${req.statut_immatriculation} · ${req.etat}`} />
      <Row label="Adresse du domicile" value={req.adresse_domicile} />
      <Row label="Administrateurs" value={(req.administrateurs || []).map((a) => `${a.nom} — ${a.fonction}`).join(" ; ")} />
    </div>
  );
}

export function OqlfInscriptionForm({ dossier, onUpdated, onDirtyChange }) {
  const [d, setD] = useState(dossier.oqlf_data || {});
  const [busy, setBusy] = useState(false);
  const [reqBusy, setReqBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const autoFetched = useRef(false);
  const set = (k, v) => { setD((p) => ({ ...p, [k]: v })); setDirty(true); };

  useEffect(() => { onDirtyChange?.(dirty); }, [dirty, onDirtyChange]);

  // Avertissement navigateur (fermeture / rafraîchissement) si modifications non enregistrées
  useEffect(() => {
    const handler = (e) => { if (dirty) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const fetchReq = async (neqValue, { auto = false } = {}) => {
    const neq = (neqValue || "").trim();
    if (!neq) { if (!auto) toast.error("Saisissez d'abord un NEQ"); return; }
    setReqBusy(true);
    try {
      const { data } = await api.get(`/req/lookup`, { params: { neq } });
      setD((prev) => mapReqToOqlf(data, prev));
      setDirty(true);
      if (!auto) toast.success("Formulaire pré-rempli depuis le Registraire");
    } catch (e) { if (!auto) toast.error("Récupération impossible (NEQ à 9-10 chiffres)"); }
    finally { setReqBusy(false); }
  };

  useEffect(() => {
    if (autoFetched.current) return;
    const neq = dossier.oqlf_data?.neq || dossier.neq;
    if (neq && !dossier.oqlf_data?._req) {
      autoFetched.current = true;
      fetchReq(neq, { auto: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dossier.id]);

  const remaining = ALL_FIELDS.filter(
    (f) => f.source === "entrevue" && (!f.showIf || f.showIf(d)) && isEmpty(d[f.k])
  );

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.patch(`/dossiers/${dossier.id}/oqlf`, { oqlf_data: d });
      toast.success("Formulaire d'inscription enregistré");
      setDirty(false);
      onUpdated(data);
    } catch (e) { toast.error("Erreur"); }
    finally { setBusy(false); }
  };

  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-5 space-y-5" data-testid="oqlf-inscription-form">
      <div className="flex items-center gap-2">
        <ClipboardList size={18} className="text-blue-600" />
        <h4 className="font-display font-bold text-[#0F2B48]">Formulaire d'inscription à l'Office</h4>
      </div>
      <p className="text-xs text-slate-500">
        Les champs marqués <span className="font-semibold text-emerald-700">REQ</span> sont pré-remplis automatiquement à partir du registre des entreprises.
        Complétez les champs <span className="font-semibold text-amber-700">à compléter</span> lors de l'entrevue, puis produisez le formulaire (PDF) pour révision et envoi à l'Office.
      </p>

      {/* Bloc REQ */}
      <div className="flex flex-wrap items-end gap-2 rounded-lg border border-emerald-200 bg-white/70 p-3">
        <div className="flex-1 min-w-[180px] space-y-1.5">
          <Label className="text-xs flex items-center gap-1"><Building2 size={13} className="text-emerald-700" /> NEQ (Registraire des entreprises)</Label>
          <Input value={d.neq ?? ""} placeholder="ex. 1173456789" data-testid="oqlf-neq-lookup"
            onChange={(e) => set("neq", e.target.value)} />
        </div>
        <Button size="sm" onClick={() => fetchReq(d.neq)} disabled={reqBusy} data-testid="req-fetch-btn"
          className="bg-emerald-700 hover:bg-emerald-700/90">
          {reqBusy ? <Loader2 size={15} className="mr-1 animate-spin" /> : <RefreshCw size={15} className="mr-1" />}
          {reqBusy ? "Récupération…" : "Pré-remplir depuis le REQ"}
        </Button>
      </div>

      <ReqPanel req={d._req} />

      {/* Compteur de questions d'entrevue */}
      <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50/60 px-3 py-2 text-xs" data-testid="oqlf-remaining-banner">
        <CircleHelp size={15} className="text-amber-600" />
        {remaining.length === 0
          ? <span className="font-medium text-emerald-700">Toutes les questions d'entrevue sont complétées.</span>
          : <span className="text-amber-800"><span className="font-bold" data-testid="oqlf-remaining-count">{remaining.length}</span> question(s) d'entrevue à compléter avant l'envoi.</span>}
      </div>

      {/* Sections */}
      {SECTIONS.map((sec) => (
        <div key={sec.titre} className="space-y-3">
          <h5 className="font-display text-sm font-bold text-[#0F2B48] border-b border-blue-100 pb-1">{sec.titre}</h5>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {sec.fields.filter((f) => !f.showIf || f.showIf(d)).map((f) => (
              <OqlfField key={f.k} field={f} d={d} set={set} />
            ))}
          </div>
        </div>
      ))}

      <div className="flex flex-wrap items-center gap-2 pt-1">
        <Button size="sm" onClick={save} disabled={busy} data-testid="oqlf-save" className="bg-[#0F2B48] hover:bg-[#0F2B48]/90">
          <Send size={15} className="mr-1" /> {busy ? "Enregistrement…" : "Enregistrer le formulaire"}
        </Button>
        <Button size="sm" variant="outline" data-testid="oqlf-export"
          onClick={() => downloadPdf(`/dossiers/${dossier.id}/export/oqlf`, `formulaire_inscription_oqlf_${dossier.neq || dossier.id}.pdf`).catch(() => toast.error("Erreur PDF"))}>
          <FileDown size={15} className="mr-1" /> Produire le formulaire (PDF)
        </Button>
        {dirty && (
          <span className="flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800" data-testid="oqlf-unsaved-badge">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" /> Modifications non enregistrées
          </span>
        )}
      </div>
    </div>
  );
}
