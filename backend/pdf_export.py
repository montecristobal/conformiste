"""Génération de PDF fidèles pour transmission manuelle à l'OQLF (aucune API)."""
from io import BytesIO
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

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


def _fmt(v):
    if isinstance(v, list):
        if v and isinstance(v[0], dict):
            return "; ".join(", ".join(f"{kk}: {vv}" for kk, vv in row.items()) for row in v)
        return ", ".join(str(x) for x in v)
    if isinstance(v, bool):
        return "Oui" if v else "Non"
    return str(v)


def build_module1_pdf(dossier):
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
