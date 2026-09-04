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

## Implémenté (2026-06 — itération 2, moteur d'analyse)
- Téléversement réel de fichiers (stockage d'objets Emergent) — corrige le placeholder des champs fichier du Module 1.
- Extraction de contenu : PDF (pdfplumber), images (OCR via LLM vision), sites web (scraping serveur + anti-SSRF).
- Analyse LLM (OpenAI gpt-5.4, clé universelle Emergent) : détection de langue + constats factuels routés vers les thèmes du catalogue.
- PRINCIPE DE PRUDENCE : drapeau `texte_loi_valide` par thème (tous à false). Constats en « à valider par un professionnel », jamais « non conforme » tant que non validé.
- Plan de correction consolidé (constat, statut, mesure suggérée, échéance figée, coût), convertible en mesure du Module 2 d'un clic.
- Brouillon de courriel OQLF (objet + corps + PDF téléchargé + lien mailto ; envoi manuel, jamais automatique).
- Suppression (soft-delete) de documents, validation MIME/taille des uploads, I/O non bloquante (run_in_threadpool), lockout anti-force-brute sur email.
- Tests : 68/69 pytest + parcours frontend complet validés (rapports iteration_3 & iteration_4).

## Hors périmètre / backlog

## Implémenté (2026-06 — itération 3)
- Rappels d'échéance automatiques J-30 / J-7 (+ retard) : tâche planifiée quotidienne (.emergent/crons.yml → /api/v1/cron/reminders, auth Bearer WEBHOOK_CRON_SECRET), notifications par utilisateur, cloche + panneau dans l'en-tête.
- Vignettes des photos téléversées dans la liste des documents (onglet Analyse).
- Préparation passive CLF-Expert : versionnage API `/api/v1`, champs externes nullables (external_*, reference_date, retrieved_at) sur thèmes et mesures, module inerte `clf_expert_client.py` (aucun appel réseau).
- Robustesse : retry/backoff sur le stockage d'objets (5xx transitoires), insertion de notifications protégée contre les doublons concurrents.
- Tests : 87/87 pytest + parcours frontend validés (rapport iteration_5).

## Implémenté (2026-06 — itération 4)
- Validation d'un thème : A5 (Affichage public & publicité commerciale) passé à `texte_loi_valide=true` avec texte de loi (art. 58) et citation externe ; le moteur qualifie désormais « non conforme » sur A5 (les autres thèmes restent « à valider »).
- Regroupement des rappels : le panneau de notifications regroupe par dossier (rappel le plus urgent en tête, badge « N rappels »), badge de non-lus compté par dossier.
- Rappels par courriel : envoi Resend géré par Emergent (mailer.py + gate de sécurité), en plus des notifications in-app, déclenché par la génération de rappels (destinataire = propriétaire du dossier, gabarit serveur, lien https vers le dossier).

## Prochaines tâches (mis à jour)
- Faire basculer des thèmes à `texte_loi_valide=true` (au cas par cas, après validation du texte légal) pour activer les qualifications de niveau 2.
- Rappels d'échéance automatiques J-30 / J-7.
- Paiements/abonnements Stripe pour les plans PRO/SOLO.
- Optionnel : vérification magic bytes des fichiers, DNS-rebinding, split de server.py en routers.

## Backlog historique (itération 1)
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
