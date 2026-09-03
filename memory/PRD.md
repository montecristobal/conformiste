# CONFORMISTE — PRD

## Problème / Vision
SaaS de gestion de dossiers de francisation (Charte de la langue française du Québec / Loi 96),
sur le modèle des logiciels de production de rapports d'impôt. Deux versions : **PRO** (consultant
multi-clients, cloisonnement par client) et **SOLO** (entreprise, dossier unique guidé). SOLO par défaut.
Transmission à l'OQLF hors application : export PDF fidèle uniquement (aucune API publique).

## Architecture
- Backend : FastAPI + MongoDB (motor), routes `/api`, JWT email/mot de passe (bcrypt, cookie httpOnly + Bearer), anti-force brute (429 après 5 échecs).
- PDF : reportlab (`pdf_export.py`). Catalogue légal & pipeline : `catalogue.py`.
- Frontend : React 19 + React Router + Tailwind + shadcn/ui + sonner. Design institutionnel (bleu Québec).

## Personas
- Consultant·e en francisation (PRO) — gère plusieurs dossiers clients.
- Entreprise < 100 employés (SOLO) — gère son propre dossier.

## Exigences centrales (statiques)
- Accueil PRO/SOLO (SOLO défaut) avec explication de chaque mode.
- Auth JWT ; PRO multi-clients / SOLO dossier unique ; cloisonnement des données.
- Tableau de bord trié par échéance légale la plus proche.
- Cycle de vie du dossier en 8 étapes (statuts, dates limites, historique d'échanges OQLF).
- Module 1 — Analyse de la situation linguistique (11 sections + Annexes I/II, logique conditionnelle).
- Module 2 — Programme de francisation (catalogue thèmes Niveau A/B, mesures répétables ; base RMO prête).
- Export PDF Module 1 & Module 2. Journal d'audit horodaté par dossier.

## Implémenté (2026-06 — itération 1, squelette)
- Auth JWT email/mot de passe + compte propriétaire vild@yuville.com (PRO) + anti-force brute.
- Accueil PRO/SOLO, inscription/connexion, routes protégées, ProOnly pour /clients.
- Clients (PRO) : création + cloisonnement par propriétaire.
- Dossiers : CRUD (create/list/get/patch), calcul auto échéance Module 1 (+3 mois), urgence, tri par échéance.
- Pipeline 8 étapes : statut (validé par enum), date limite, note, historique d'échanges OQLF.
- Module 1 : formulaire piloté par schéma (11 sections + Annexes I/II conditionnelles), tables répétables, multicheck, sync employés/établissements.
- Module 2 : catalogue 5 thèmes A + 9 thèmes B (texte_loi = placeholder volontaire), mesures répétables + statut_mise_en_oeuvre (base RMO).
- Export PDF Module 1 & 2 (téléchargement blob + Bearer). Journal d'audit horodaté + checksum + export CSV.
- Tests : 33 tests pytest (32 pass) + flux frontend PRO/SOLO validés par l'agent de test.

## Hors périmètre itération 1 (backlog)
- P1 : Paiements/abonnements Stripe (plans PRO/SOLO) — demandé, reporté.
- P1 : Téléversement réel des pièces jointes (object storage) — actuellement nom de document texte seulement.
- P1 : Interface RMO (rapport de mise en œuvre) — modèle de données déjà prêt (statut_mise_en_oeuvre).
- P2 : Texte légal validé article par article pour `texte_loi` (placeholder aujourd'hui).
- P2 : Autres formulaires (inscription, suivis triennaux), dossier de preuves, notifications/rappels J-30/J-7.
- P2 : PUT/DELETE clients & dossiers ; sélecteur de date localisé fr-CA.

## Prochaines tâches
1. Rappels d'échéance J-30 / J-7 (visuels + éventuel courriel Resend).
2. Téléversement réel des pièces jointes (object storage).
3. Paiements Stripe pour activer les plans PRO/SOLO.
