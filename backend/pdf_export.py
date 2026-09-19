"""Génération de PDF fidèles pour transmission manuelle à l'OQLF (aucune API)."""
from io import BytesIO
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    Image as RLImage, PageBreak,
)
from reportlab.lib.utils import ImageReader

NAVY = colors.HexColor("#0F2B48")
AZUR = colors.HexColor("#2563EB")
SLATE = colors.HexColor("#475569")
LIGHT = colors.HexColor("#F1F5F9")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="Gov", parent=ss["Title"], fontSize=16, textColor=NAVY,
                          spaceAfter=2, alignment=0))
    ss.add(ParagraphStyle(name="GovSub", parent=ss["Normal"], fontSize=9, textColor=SLATE,
                          spaceAfter=2))
    ss.add(ParagraphStyle(name="H1", parent=ss["Heading1"], fontSize=13, textColor=NAVY,
                          spaceBefore=14, spaceAfter=6))
    ss.add(ParagraphStyle(name="H2", parent=ss["Heading2"], fontSize=11, textColor=AZUR,
                          spaceBefore=10, spaceAfter=4))
    ss.add(ParagraphStyle(name="Body", parent=ss["Normal"], fontSize=9.5, leading=13,
                          textColor=colors.HexColor("#0F172A")))
    ss.add(ParagraphStyle(name="Label", parent=ss["Normal"], fontSize=8.5,
                          textColor=SLATE))
    ss.add(ParagraphStyle(name="Legal", parent=ss["Normal"], fontSize=8, leading=11,
                          textColor=SLATE, backColor=LIGHT, borderPadding=4))
    return ss


def _header(story, ss, titre, sous_titre):
    story.append(Paragraph("Office québécois de la langue française", ss["Gov"]))
    story.append(Paragraph("Direction de la francisation — Charte de la langue française (Loi 96)",
                           ss["GovSub"]))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph(titre, ss["H1"]))
    if sous_titre:
        story.append(Paragraph(sous_titre, ss["Body"]))
    story.append(Spacer(1, 6))


def _kv_table(rows):
    data = [[k, v if v not in (None, "") else "—"] for k, v in rows]
    t = Table(data, colWidths=[6.2 * cm, 10.3 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), SLATE),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#0F172A")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(SLATE)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    canvas.drawString(2 * cm, 1 * cm, f"CONFORMISTE — Document généré le {stamp}")
    canvas.drawRightString(19.5 * cm, 1 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _esc(v):
    return (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _fmt(v):
    if isinstance(v, list):
        if v and isinstance(v[0], dict):
            return "; ".join(", ".join(f"{kk}: {vv}" for kk, vv in row.items()) for row in v)
        return ", ".join(str(x) for x in v)
    if isinstance(v, bool):
        return "Oui" if v else "Non"
    return str(v)


def build_module1_pdf(dossier, proof_images=None):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    ss = _styles()
    story = []
    _header(story, ss,
            "Analyse de la situation linguistique",
            f"Entreprise : <b>{dossier.get('nom_entreprise', '—')}</b> — NEQ : {dossier.get('neq', '—')}")

    data = dossier.get("module1_data", {}) or {}
    meta = dossier.get("module1_meta", {}) or {}
    sections = meta.get("sections", [])
    labels = meta.get("labels", {})

    if not sections:
        story.append(Paragraph("<i>Le formulaire n'a pas encore été rempli.</i>", ss["Label"]))
    for sec in sections:
        story.append(Paragraph(sec.get("titre", ""), ss["H2"]))
        rows = []
        for key in sec.get("field_keys", []):
            if key in data and data[key] not in (None, "", []):
                rows.append((labels.get(key, key), _fmt(data[key])))
        if rows:
            story.append(_kv_table(rows))
        else:
            story.append(Paragraph("<i>Aucune réponse saisie.</i>", ss["Label"]))
        story.append(Spacer(1, 4))

    if proof_images:
        story.append(PageBreak())
        story.append(Paragraph("Annexe — Preuves linguistiques (captures d'écran horodatées)", ss["H2"]))
        story.append(Paragraph(
            "Captures réalisées automatiquement par CONFORMISTE à des fins de preuve de la langue "
            "affichée sur le site Web et les médias sociaux de l'entreprise.", ss["Label"]))
        story.append(Spacer(1, 8))
        max_w = doc.width
        for caption, img_bytes in proof_images:
            try:
                reader = ImageReader(BytesIO(img_bytes))
                iw, ih = reader.getSize()
                w = min(max_w, iw)
                h = w * ih / iw
                max_h = 20 * cm
                if h > max_h:
                    h = max_h
                    w = h * iw / ih
                story.append(Paragraph(caption, ss["Label"]))
                story.append(Spacer(1, 3))
                story.append(RLImage(BytesIO(img_bytes), width=w, height=h))
                story.append(Spacer(1, 12))
            except Exception:
                continue

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf


def build_inscription_pdf(dossier):
    ins = dossier.get("inscription_data", {}) or {}
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    ss = _styles()
    story = []
    _header(story, ss, "Demande d'inscription de l'entreprise",
            f"Entreprise : <b>{dossier.get('nom_entreprise', '—')}</b>")
    story.append(_kv_table([
        ("Nom de l'entreprise", dossier.get("nom_entreprise")),
        ("NEQ", ins.get("neq") or dossier.get("neq")),
        ("Adresse", ins.get("adresse")),
        ("Personne-ressource", ins.get("personne_ressource")),
        ("Courriel", ins.get("courriel")),
        ("Téléphone", ins.get("telephone")),
        ("Nombre d'employés au Québec", ins.get("nb_employes_quebec", dossier.get("nb_employes_quebec"))),
        ("Nombre d'établissements", ins.get("nb_etablissements", dossier.get("nb_etablissements"))),
        ("Comité de francisation requis", "Oui (100 employés ou plus)" if (dossier.get("nb_employes_quebec") or 0) >= 100 else "Non"),
        ("Activités / secteur", ins.get("activites")),
    ]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Document produit à partir de l'entrevue d'inscription. À réviser puis transmettre "
        "à l'Office québécois de la langue française.", ss["Label"]))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf


OQLF_LAYOUT = [
    ("Informations générales", [
        ("prise_connaissance", "Comment avez-vous pris connaissance de l'obligation de vous inscrire ?"),
        ("prise_connaissance_autre", "Autres (précisez)"),
    ]),
    ("1. Renseignements sur l'identité de l'entreprise", [
        ("nom_entreprise", "Nom de l'entreprise (tel qu'immatriculé au registre du Québec)"),
        ("neq", "Numéro d'entreprise du Québec (NEQ)"),
        ("autres_noms", "Autres noms utilisés au Québec"),
        ("site_web", "Site Web"),
        ("etab_principal_adresse", "Principal établissement — numéro, rue, local ou bureau"),
        ("etab_principal_ville_cp", "Ville et code postal"),
    ]),
    ("2. Responsable de la direction au Québec", [
        ("resp_civilite", "Civilité"),
        ("resp_prenom", "Prénom"),
        ("resp_nom", "Nom"),
        ("resp_titre", "Titre ou fonction"),
        ("resp_courriel", "Courriel"),
        ("resp_telephone", "Téléphone"),
        ("resp_poste", "Poste"),
        ("resp_telecopieur", "Télécopieur"),
        ("resp_adresse", "Adresse — numéro, rue, local ou bureau"),
        ("resp_ville_cp", "Ville et code postal"),
    ]),
    ("3. Personne-ressource auprès de l'Office (si différente de la section 2)", [
        ("pr_differente", "Une personne-ressource différente du responsable ?"),
        ("pr_civilite", "Civilité"),
        ("pr_prenom", "Prénom"),
        ("pr_nom", "Nom"),
        ("pr_titre", "Titre ou fonction"),
        ("pr_courriel", "Courriel"),
        ("pr_telephone", "Téléphone"),
        ("pr_poste", "Poste"),
        ("pr_telecopieur", "Télécopieur"),
        ("pr_adresse", "Adresse — numéro, rue, local ou bureau"),
        ("pr_ville_cp", "Ville et code postal"),
    ]),
    ("4. Activités commerciales de l'entreprise au Québec", [
        ("activites_principales", "4.1 Quelles sont les principales activités de l'entreprise ?"),
        ("activites_economiques", "4.2 Activités économiques (telles qu'au REQ)"),
        ("codes_cae", "Codes d'activités économiques (CAE)"),
    ]),
    ("5. Structure de l'entreprise au Québec", [
        ("deja_50_plus", "5.1 A déjà employé 50 personnes ou plus durant 6 mois au Québec ?"),
        ("nb_employes_actuel", "5.2 Nombre de personnes employées actuellement (tous statuts)"),
        ("nb_etablissements", "5.3 Nombre d'établissements au Québec"),
        ("etablissements_villes", "5.3 Ville(s) où ils sont situés"),
        ("siege_au_quebec", "5.4 Le siège social de l'entreprise est-il au Québec ?"),
        ("siege_lieu", "5.4 Si non, lieu (ville et pays)"),
        ("gere_admin", "5.5 Gère-t-elle elle-même ses fonctions administratives au Québec ?"),
        ("gere_admin_precision", "5.5 Si non ou en partie, expliquez"),
        ("centre_recherche", "5.6 A-t-elle un centre de recherche au Québec ?"),
        ("centre_recherche_domaines", "5.6 Si oui, domaines de recherche"),
        ("etab_hors_quebec", "5.7 Possède-t-elle des établissements à l'extérieur du Québec ?"),
    ]),
    ("6. Attestation du ou de la responsable de la direction au Québec", [
        ("att_prenom", "Prénom"),
        ("att_nom", "Nom"),
        ("att_titre", "Titre ou fonction"),
        ("att_date", "Date"),
    ]),
]


def build_oqlf_pdf(dossier):
    data = dossier.get("oqlf_data", {}) or {}
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    ss = _styles()
    story = []
    _header(story, ss, "Formulaire d'inscription à l'Office",
            f"Entreprise : <b>{_esc(data.get('nom_entreprise') or dossier.get('nom_entreprise', '—'))}</b> "
            f"— NEQ : {_esc(data.get('neq') or dossier.get('neq', '—'))}")

    def oqlf_table(fields):
        rows = []
        for fid, label in fields:
            v = data.get(fid)
            val = _fmt(v) if v not in (None, "", []) else "—"
            rows.append([Paragraph(_esc(label), ss["Label"]),
                         Paragraph(_esc(val), ss["Body"])])
        t = Table(rows, colWidths=[8 * cm, 8.5 * cm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (0, -1), 10),
        ]))
        return t

    for titre, fields in OQLF_LAYOUT:
        story.append(Paragraph(titre, ss["H2"]))
        story.append(oqlf_table(fields))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "J'atteste que les renseignements contenus dans ce document sont exacts et représentent "
        "la situation actuelle de l'entreprise.", ss["Legal"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Document produit à partir du registre des entreprises (REQ) et de l'entrevue d'inscription. "
        "À réviser par le ou la responsable, puis à transmettre à l'Office québécois de la langue française.",
        ss["Label"]))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf


_PLAINTE_STATUT_LABELS = {"a_faire": "À faire", "en_cours": "En cours", "fait": "Fait", "sans_objet": "Sans objet"}
_PLAINTE_RES_LABELS = {"amiable": "Résolue à l'amiable", "classee": "Classée (non fondée)",
                       "infirmee": "Ordonnance infirmée", "amende": "Amende / jugement"}
_PLAINTE_TYPE_LABELS = {"inspection": "Visite d'un inspecteur", "lettre": "Lettre de l'OQLF"}


def build_plainte_pdf(dossier, pieces_by_stage=None):
    """Dossier de plainte horodaté : chronologie, échanges et pièces (preuve de suivi)."""
    pieces_by_stage = pieces_by_stage or {}
    pl = dossier.get("plainte") or {}
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    ss = _styles()
    story = []
    _header(story, ss, "Dossier de plainte — suivi",
            f"Entreprise : <b>{_esc(dossier.get('nom_entreprise', '—'))}</b> — "
            f"NEQ : {_esc(dossier.get('neq', '—'))}")
    story.append(_kv_table([
        ("Référence OQLF", pl.get("reference_oqlf") or "—"),
        ("Communication initiale", _PLAINTE_TYPE_LABELS.get(pl.get("type_communication"), "—")),
        ("Statut du dossier", "Ouvert" if pl.get("ouverte") else "Clos"),
        ("Résolution", _PLAINTE_RES_LABELS.get(pl.get("resolution"), "En cours")),
        ("Ouvert le", (pl.get("created_at") or "")[:10] or "—"),
    ]))
    story.append(Spacer(1, 6))
    for s in pl.get("stages", []):
        story.append(Paragraph(
            f'{s.get("ordre")}. {_esc(s.get("label", ""))} — '
            f'<b>{_PLAINTE_STATUT_LABELS.get(s.get("statut"), s.get("statut"))}</b>', ss["H2"]))
        rows = []
        if s.get("date"):
            rows.append(("Date de l'événement", s["date"]))
        if s.get("date_limite"):
            rows.append(("Échéance", s["date_limite"]))
        if s.get("note"):
            rows.append(("Note", s["note"]))
        if rows:
            story.append(_kv_table(rows))
        for h in s.get("historique", []):
            story.append(Paragraph(
                f'Échange — {_esc((h.get("date") or "")[:16])} · {_esc(h.get("auteur", ""))} : '
                f'{_esc(h.get("texte", ""))}', ss["Legal"]))
        for fn in pieces_by_stage.get(s.get("key"), []):
            story.append(Paragraph(f'Pièce jointe : {_esc(fn)}', ss["Label"]))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Document produit par CONFORMISTE à titre de preuve de suivi. Ne constitue pas un avis juridique.",
        ss["Label"]))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf


def build_regime_a_pdf(dossier, themes, findings_by_theme):
    """Rapport de conformité aux obligations universelles (Régime A, < 25 employés)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    ss = _styles()
    story = []
    _header(story, ss, "Rapport de conformité — Obligations universelles",
            f"Entreprise : <b>{_esc(dossier.get('nom_entreprise', '—'))}</b> — "
            f"NEQ : {_esc(dossier.get('neq', '—'))}")

    story.append(Paragraph(
        "Entreprise de moins de 25 employés — assujettie aux obligations générales des chapitres VI "
        "(langue du travail) et VII (langue du commerce et des affaires) de la Charte de la langue "
        "française. Aucun parcours de francisation, analyse linguistique ou certificat ne s'applique "
        "à ce régime.", ss["Body"]))
    story.append(Spacer(1, 4))

    ordered = sorted(themes, key=lambda x: (not x.get("prioritaire_amorce", True), x.get("ordre", 0)))
    evalues = sum(1 for t in ordered if findings_by_theme.get(t["id"]))
    story.append(Paragraph(
        f"{evalues} thème(s) évalué(s) sur {len(ordered)}. Estimation indicative — à valider par un "
        "professionnel.", ss["Label"]))
    story.append(Spacer(1, 6))

    for t in ordered:
        fs = findings_by_theme.get(t["id"], [])
        if not fs:
            statut = "Non évalué"
        elif any(f.get("statut") == "non_conforme" for f in fs):
            statut = "Non conforme"
        else:
            statut = "À valider"
        story.append(Paragraph(
            f'{t["id"]} — {_esc(t.get("nom_theme", ""))} ({_esc(t.get("article", ""))}) — '
            f'<b>{statut}</b>', ss["H2"]))
        tl = t.get("texte_loi") or "[Texte légal non disponible]"
        story.append(Paragraph(f"Texte de loi : {_esc(tl)}", ss["Legal"]))
        if fs:
            for i, f in enumerate(fs, 1):
                story.append(_kv_table([
                    (f"Constat {i}", f.get("constat")),
                    ("Source", f.get("source")),
                    ("Mesure suggérée", f.get("mesure_suggeree")),
                    ("Statut", {"non_conforme": "Non conforme", "a_valider": "À valider"}.get(f.get("statut"), f.get("statut"))),
                ]))
                story.append(Spacer(1, 3))
        else:
            story.append(Paragraph("<i>Aucun constat — thème non encore évalué par l'analyse.</i>", ss["Label"]))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Document produit par CONFORMISTE à titre indicatif à partir des documents et médias analysés. "
        "Ne constitue pas un avis juridique.", ss["Label"]))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf


def build_module2_pdf(dossier, themes, comite_requis):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    ss = _styles()
    story = []
    admin = dossier.get("module2_admin", {}) or {}
    _header(story, ss, "Programme de francisation (PF)",
            f"Entreprise : <b>{dossier.get('nom_entreprise', '—')}</b> — NEQ : {dossier.get('neq', '—')}")

    story.append(_kv_table([
        ("Numéro de dossier OQLF", admin.get("numero_dossier_oqlf")),
        ("Numéro de prolongation", admin.get("numero_prolongation")),
        ("Nombre d'employés au Québec", dossier.get("nb_employes_quebec")),
    ]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Droits en vertu de la Charte", ss["H2"]))
    story.append(Paragraph(
        "Les articles 2, 4 et 5 de la Charte de la langue française garantissent au personnel "
        "le droit de travailler en français. (Texte informatif — contenu légal validé "
        "ultérieurement.)", ss["Legal"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Application du programme", ss["H2"]))
    story.append(Paragraph(
        "L'entreprise s'engage à mettre en œuvre le présent programme et à transmettre un "
        "rapport de mise en œuvre tous les 12 mois. (Texte informatif.)", ss["Legal"]))

    if comite_requis:
        story.append(Spacer(1, 4))
        story.append(Paragraph("Comité de francisation", ss["H2"]))
        story.append(Paragraph(
            "L'entreprise comptant 100 employés ou plus institue un comité de francisation. "
            "(Texte informatif.)", ss["Legal"]))

    mesures = dossier.get("module2_mesures", []) or []
    by_theme = {}
    for m in mesures:
        by_theme.setdefault(m.get("theme_id"), []).append(m)

    for niveau, titre in [("A", "Niveau A — Obligations exécutoires universelles"),
                          ("B", "Niveau B — Objectifs de généralisation (art. 141)")]:
        story.append(Paragraph(titre, ss["H1"]))
        for th in [t for t in themes if t["niveau"] == niveau]:
            story.append(Paragraph(th["nom_theme"], ss["H2"]))
            story.append(Paragraph(f"Libellé OQLF : {th['libelle_oqlf']}", ss["Label"]))
            tl = th.get("texte_loi") or "[Texte légal à valider — placeholder]"
            story.append(Paragraph(f"Texte de loi : {tl}", ss["Legal"]))
            th_mesures = by_theme.get(th["id"], [])
            if not th_mesures:
                story.append(Paragraph("<i>Aucune mesure ajoutée.</i>", ss["Label"]))
            for i, m in enumerate(th_mesures, 1):
                ech = m.get("echeance")
                if isinstance(ech, list):
                    ech = "; ".join(f"phase {p.get('phase')}: {p.get('date')}" for p in ech)
                rows = [
                    (f"Mesure {i} — engagement", m.get("mesure_engagee")),
                    ("Précisions de l'entreprise", m.get("precisions_entreprise")),
                    ("Commentaire de l'Office", m.get("precisions_oqlf")),
                    ("Proposition de l'Office", m.get("propositions_oqlf")),
                    ("Échéance", ech),
                    ("Statut de mise en œuvre", m.get("statut_mise_en_oeuvre")),
                ]
                story.append(_kv_table(rows))
                story.append(Spacer(1, 4))
            story.append(Spacer(1, 4))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf



# ----------------------------------------------------------------- Gantt export
from datetime import date, timedelta

_GA_COLORS = {"non_evalue": "#CBD5E1", "conforme": "#10B981", "a_valider": "#F59E0B",
              "non_conforme": "#EF4444", "sans_objet": "#E2E8F0"}
_GFR_COLORS = {"a_faire": "#94A3B8", "en_cours": "#3B82F6", "completee": "#10B981", "reportee": "#F59E0B"}
_G_INCONT = "#EF4444"
_GA_LEGEND = [("Non évalué", "#CBD5E1"), ("Conforme", "#10B981"), ("À valider", "#F59E0B"),
              ("Non conforme", "#EF4444"), ("Incontournable", "#EF4444")]
_GFR_LEGEND = [("À faire", "#94A3B8"), ("En cours", "#3B82F6"), ("Complétée", "#10B981"),
               ("Reportée", "#F59E0B"), ("Incontournable", "#EF4444")]


def _g_parse(s):
    try:
        return datetime.fromisoformat(s).date() if s else None
    except Exception:
        return None


def _g_eff(saved, today, sk, ek):
    from dateutil.relativedelta import relativedelta
    saved = saved or {}
    planned = bool(saved.get(sk) or saved.get(ek))
    debut = _g_parse(saved.get(sk)) or today
    echeance = _g_parse(saved.get(ek)) or (debut + relativedelta(months=3))
    if echeance < debut:
        echeance = debut + relativedelta(months=3)
    return planned, debut, echeance


def build_gantt_pdf(dossier, kind, themes):
    """Diagramme de Gantt (paysage, une page à hauteur dynamique) pour transmission/archivage."""
    from reportlab.pdfgen import canvas
    from dateutil.relativedelta import relativedelta

    today = datetime.now(timezone.utc).date()
    rows = []
    if kind == "parcours_a":
        els = dossier.get("parcours_a_elements") or {}
        cmap, legend = _GA_COLORS, _GA_LEGEND
        ordered = sorted(themes, key=lambda x: (not x.get("prioritaire_amorce", True), x.get("ordre", 0)))
        for t in ordered:
            saved = els.get(t["id"]) or {}
            planned, deb, ech = _g_eff(saved, today, "date_debut", "date_echeance")
            rows.append({"badge": t["id"], "label": t.get("nom_theme", ""),
                         "statut": saved.get("statut") or "non_evalue",
                         "inc": bool(saved.get("incontournable")),
                         "planned": planned, "debut": deb, "echeance": ech})
        if dossier.get("req_declaration_requise"):
            saved = els.get("REQ") or {}
            planned, deb, ech = _g_eff(saved, today, "date_debut", "date_echeance")
            inc = saved.get("incontournable")
            rows.append({"badge": "REQ", "label": "Déclaration au registraire des entreprises (REQ)",
                         "statut": saved.get("statut") or "non_evalue",
                         "inc": True if inc is None else bool(inc),
                         "planned": planned, "debut": deb, "echeance": ech})
        title = "Diagramme de Gantt — Mise en conformité (obligations universelles)"
    else:
        mesures = dossier.get("module2_mesures") or []
        cmap, legend = _GFR_COLORS, _GFR_LEGEND
        tname = {t["id"]: t["nom_theme"] for t in themes}
        for i, m in enumerate(mesures):
            planned, deb, ech = _g_eff(m, today, "date_debut", "echeance")
            label = (m.get("mesure_engagee") or "").strip() or \
                f"{tname.get(m.get('theme_id'), m.get('theme_id'))} — mesure {i + 1}"
            rows.append({"badge": m.get("theme_id"), "label": label,
                         "statut": m.get("statut_mise_en_oeuvre") or "a_faire",
                         "inc": bool(m.get("incontournable")),
                         "planned": planned, "debut": deb, "echeance": ech})
        title = "Diagramme de Gantt — Mesures du programme de francisation"

    if rows:
        mn = min([today] + [r["debut"] for r in rows])
        mx = max([today + relativedelta(months=3)] + [r["echeance"] for r in rows])
    else:
        mn, mx = today, today + relativedelta(months=3)
    start = mn - timedelta(days=mn.weekday())
    end = mx + timedelta(days=((7 - mx.weekday()) % 7) or 7)
    weeks = []
    cur = start
    while cur < end:
        weeks.append(cur)
        cur = cur + timedelta(days=7)
    total_days = max(1, (end - start).days)

    margin, label_w, col_w, row_h = 28, 214, 24, 20
    n = max(1, len(rows))
    page_w = max(660, margin * 2 + label_w + len(weeks) * col_w)
    page_h = max(280, margin * 2 + 92 + n * row_h)
    chart_x0 = margin + label_w
    chart_w = len(weeks) * col_w

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))

    # En-tête
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(margin, page_h - margin - 4, title)
    c.setFont("Helvetica", 9)
    c.setFillColor(SLATE)
    c.drawString(margin, page_h - margin - 20,
                 f"Entreprise : {dossier.get('nom_entreprise', '—')}  ·  NEQ : {dossier.get('neq', '—')}  "
                 f"·  Généré le {today.isoformat()}  ·  Échelle : semaines")
    # Légende
    lx = margin
    ly = page_h - margin - 38
    c.setFont("Helvetica", 7.5)
    for lab, col in legend:
        c.setFillColor(colors.HexColor(col))
        c.roundRect(lx, ly - 2, 14, 8, 2, fill=1, stroke=0)
        c.setFillColor(SLATE)
        c.drawString(lx + 18, ly, lab)
        lx += 22 + c.stringWidth(lab, "Helvetica", 7.5) + 12

    grid_top = page_h - (margin + 74)
    grid_bottom = grid_top - len(rows) * row_h

    # Colonnes semaines
    c.setLineWidth(0.4)
    for i, w in enumerate(weeks):
        x = chart_x0 + i * col_w
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(x, grid_top, x, grid_bottom)
        c.setFillColor(colors.HexColor("#94A3B8"))
        c.setFont("Helvetica", 5.5)
        c.drawString(x + 1.5, grid_top + 4, w.strftime("%d/%m"))
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.line(chart_x0 + chart_w, grid_top, chart_x0 + chart_w, grid_bottom)
    c.line(chart_x0, grid_top, chart_x0 + chart_w, grid_top)

    # Ligne aujourd'hui
    tx = chart_x0 + (today - start).days / total_days * chart_w
    c.setStrokeColor(colors.HexColor(_G_INCONT))
    c.setLineWidth(1)
    c.line(tx, grid_top + 8, tx, grid_bottom)

    # Lignes / barres
    for r_i, r in enumerate(rows):
        ytop = grid_top - r_i * row_h
        # séparateur
        c.setStrokeColor(colors.HexColor("#F1F5F9"))
        c.setLineWidth(0.4)
        c.line(margin, ytop - row_h, chart_x0 + chart_w, ytop - row_h)
        # libellé
        lab = f"[{r['badge']}] {r['label']}"
        if len(lab) > 44:
            lab = lab[:43] + "…"
        c.setFillColor(NAVY)
        c.setFont("Helvetica", 8)
        c.drawString(margin, ytop - row_h + 6, lab)
        # barre
        x1 = chart_x0 + (r["debut"] - start).days / total_days * chart_w
        x2 = chart_x0 + (r["echeance"] - start).days / total_days * chart_w
        bw = max(3, x2 - x1)
        fill = _G_INCONT if r["inc"] else cmap.get(r["statut"], "#6366F1")
        by = ytop - row_h + 4
        bh = row_h - 8
        c.setFillColor(colors.HexColor(fill))
        if not r["planned"]:
            c.setFillAlpha(0.5)
            c.setStrokeColor(colors.HexColor("#64748B"))
            c.setLineWidth(0.8)
            c.setDash(2, 2)
            c.roundRect(x1, by, bw, bh, 3, fill=1, stroke=1)
            c.setDash()
            c.setFillAlpha(1)
        else:
            stroke = colors.HexColor("#B91C1C") if r["inc"] else colors.HexColor(fill)
            c.setStrokeColor(stroke)
            c.setLineWidth(1 if r["inc"] else 0)
            c.roundRect(x1, by, bw, bh, 3, fill=1, stroke=1 if r["inc"] else 0)

    # Pied
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 7)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    c.drawString(margin, 12, f"CONFORMISTE — Diagramme généré le {stamp}. Document indicatif, ne constitue pas un avis juridique.")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def gantt_pdf_to_png(pdf_buf):
    import pymupdf
    pdf_buf.seek(0)
    doc = pymupdf.open(stream=pdf_buf.read(), filetype="pdf")
    page = doc[0]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
    out = BytesIO(pix.tobytes("png"))
    out.seek(0)
    return out
