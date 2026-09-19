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

## Implémenté (2026-06 — itération 5, mode SOLO)
- Inscription SOLO : un dossier unique est créé automatiquement à l'inscription ; l'utilisateur SOLO arrive directement sur ce dossier (cheminement en haut), sans possibilité d'ajouter d'autres dossiers (bouton « Nouveau dossier » réservé au PRO ; /dashboard redirige le SOLO vers son dossier).
- Cheminement conditionnel : l'étape « Constitution du comité de francisation » n'apparaît que si le nombre d'employés au Québec est ≥ 100 (sinon masquée).
- Entrevue d'inscription : formulaire guidé dans l'étape « Inscription » (NEQ, employés, établissements, personne-ressource, coordonnées, activités) qui produit un document d'inscription PDF ; le nombre d'employés saisi met à jour le dossier et déclenche l'apparition du comité.
- Vérifié (backend) : auto-dossier SOLO, bascule comite_requis 0→false / 120→true, export PDF inscription (application/pdf).

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

## Implémenté (2026-06 — itération 6, Pré-remplissage REQ + Formulaire OQLF)
- Pré-remplissage REQ (mode DÉMO) : endpoint `GET /api/v1/req/lookup?neq=` (validation NEQ ^\d{9,10}$, 422 sinon) renvoyant un dossier d'entreprise réaliste et déterministe (`req_lookup.simulate_req`) imitant le Registraire des entreprises du Québec. À remplacer par la vraie source (registre public temps réel ou données ouvertes Données Québec) en production.
- Formulaire d'inscription OQLF complet (6 sections, fidèle au formulaire officiel) remplaçant l'ancienne « entrevue » : composant `OqlfInscriptionForm.jsx` à l'étape Inscription.
  - Récupération automatique des données REQ à l'ouverture si un NEQ est présent (garde useRef, pas de double appel, écrasement des champs REQ) ; bouton manuel « Pré-remplir depuis le REQ ».
  - Champs REQ pré-remplis (nom, NEQ, autres noms, adresse principal établissement, activités + codes CAE, nb établissements, responsable, attestation) marqués « REQ » ; champs manquants posés en questions d'entrevue marquées « à compléter » avec compteur de questions restantes.
  - Champs conditionnels (prise_connaissance=Autres, personne-ressource différente, siège hors Québec, gestion admin partielle, centre de recherche).
  - Export PDF fidèle : `GET /api/v1/dossiers/{id}/export/oqlf` (`build_oqlf_pdf`, libellés qui s'enroulent, champs vides = « — »). Enregistrement via `PATCH /api/v1/dossiers/{id}/oqlf`.
- Vérifié : backend (save 200, req/lookup 200/422/401, export PDF 200 rendu visuel OK sur 3 pages) ; frontend testing agent 8/8 scénarios (pré-remplissage 11/11, saisie sans perte de focus 4/4, 7/7 selects, 7/7 conditionnels, persistance, PDF 200). Correction d'un bug de perte de focus (composant de champ hoisté au niveau module).

## Backlog / améliorations optionnelles (post-itération 6)
- Brancher la vraie source REQ (temps réel ou données ouvertes) à la place de la démo simulée.

## Implémenté (2026-06 — itération 7)
- **Avertissement « modifications non enregistrées »** (formulaire d'inscription OQLF) : badge visible, `beforeunload` (fermeture/rafraîchissement) et confirmation lors du changement d'étape/onglet ou du retour au tableau de bord (`OqlfInscriptionForm` + `DossierDetail`).
- **Investigation vraie source REQ** : aucune API REST publique temps réel ; site public renvoie 403 depuis le pod ; données ouvertes sous licence CC BY-NC-SA (non commerciale) + sans noms/administrateurs. Décision reportée (démo conservée). Question posée à l'utilisateur.
- **Étape 2 — Pré-remplissage par recherche Web (analyse linguistique / Module 1)** : bouton « Pré-remplir par recherche Web » qui parcourt le site Web officiel (crawler anti-SSRF `analysis.fetch_url_text`, pages accueil + à-propos/contact) puis un LLM (OpenAI gpt-5.4, clé Emergent) PROPOSE des valeurs pour des champs factuels ciblés (Sections 1, 2, 3, 8, 11). UX **accepter/refuser par proposition** + « Tout accepter/refuser » ; seuls les champs acceptés remplissent le formulaire ; source + confiance affichées. Backend `POST /api/v1/dossiers/{id}/module1/enrich` (`enrichment.py`), frontend `WebEnrichPanel.jsx` intégré à `Module1Form.jsx`.
  - Vérifié : backend curl (10 propositions correctes pour lightspeedhq.com, <30s) ; testing agent frontend 100% (panneau, accept/refuse, filtrage des refus, application, enregistrement, persistance après reload).

## Implémenté (2026-06 — itération 8, recherche Web élargie + preuve de langue)
- **Recherche Web générale (Bing, sans clé)** intégrée au pré-remplissage : `enrichment.web_search` (décodage des URL de redirection Bing) + `discover_social_urls` ; le bouton « Pré-remplir par recherche Web » utilise désormais site officiel **+ résultats de recherche Web** (titres/extraits) pour mieux trouver dirigeants et médias sociaux quand le site est pauvre.
- **Évaluation automatique de la langue + preuve** : bouton « Évaluer la langue + preuve » (Module 1) → `POST /api/v1/dossiers/{id}/language-proof`. Détection de langue déterministe (`langdetect`) du site Web et des médias sociaux (fr vs autre), **capture d'écran headless** (`screenshot.py` via google-chrome) stockée en object storage et **jointe au dossier** (documents `source=preuve-langue`), et propositions pour 8.14 (site en français) et 8.15 (médias sociaux + réseaux) avec accept/refuse. Panneau `WebEnrichPanel` enrichi d'un bloc « Preuves » + bouton « Voir la capture ».
  - Vérifié : backend curl (8.14='Non' pour site EN conf 1.0, captures PNG 1280×1600 téléchargeables et jointes) ; testing agent frontend 100% (preuve, badge langue, voir capture 200, proposition appliquée 8.14, persistance, régression enrich OK).

## Implémenté (2026-06 — itération 9, vignettes + preuve sur mesure + horodatage)
- **Vignettes inline** des captures directement dans le panneau (chargées en blob authentifié), avec **agrandissement au clic** (overlay), au lieu d'ouvrir un nouvel onglet.
- **Preuve sur mesure** : champ `module1-social-urls` pour saisir manuellement des URL de médias sociaux à capturer quand la découverte auto n'en trouve pas (passées en `social_urls[]` à l'endpoint).
- **Captures horodatées/signées** : `screenshot.stamp_proof` incruste un bandeau (PREUVE CONFORMISTE + URL + langue détectée + date/heure UTC, police LiberationSans-Bold) → preuve opposable jointe au dossier.
  - Vérifié : testing agent frontend 100% (2 vignettes <img> blob, overlay zoom, bandeau visible dans l'aperçu, download 200, proposition appliquée, save OK).

## Voie « vraie source REQ » (documentée, en attente d'identifiants)
- Aucune API REST JSON publique temps réel. Deux voies officielles :
  1. **Service Web du Registraire (RUE/CIDREQ)** — temps réel, fiable ; nécessite une entente + identifiants/certificat via le MCN (Ministère de la Cybersécurité et du Numérique). Une fois obtenus : je remplace `req_lookup.simulate_req` par un client HTTP authentifié (module `req_client.py`) avec la démo en repli.
  2. **Données ouvertes Données Québec** (ZIP 225 Mo, 6 CSV, bimensuel, NEQ = clé) — licence CC BY-NC-SA (non commerciale) et SANS noms/adresses de personnes physiques/administrateurs. J'ingère les CSV dans MongoDB (index NEQ) et interroge localement.
- Le scraping du site public renvoie 403 depuis notre serveur (non viable).

## Implémenté (2026-06 — itération 10, Module Entrevue guidée)
- **Module Entrevue guidé (style ImpôtExpert)** pour l'analyse linguistique (Module 1) : parcours **section par section** qui collecte toutes les infos restantes auprès du responsable, confirme/corrige les valeurs pré-remplies (recherche Web / preuve), avec barre de progression, navigation Précédent/Suivant (auto-enregistrement silencieux), et une **étape de Révision** (par section + boutons Modifier) avant « Terminer et enregistrer ».
- Bascule de mode **Entrevue guidée / Formulaire complet** (même état, même sauvegarde, même schéma `MODULE1_SECTIONS` + `FieldRenderer`).
- Vérifié : testing agent frontend 100% (mode par défaut entrevue, navigation, saisie persistée, bascule de mode, révision, finish + persistance après reload, régression enrich/langproof OK). Correctif : suppression du cumul de toasts (auto-save silencieux).
- ⚠️ Voie 2 REQ (données ouvertes) : **non réalisable depuis le pod** — download gouv.qc.ca 403, datastore Données Québec non exploitable (HTML). Voie 1 (Service Web MCN) reste ouverte sur fourniture d'identifiants.

## Implémenté (2026-06 — itération 11, annexe preuves PDF + guide questions restantes)
- **Annexe « Preuves linguistiques » dans le PDF Module 1** : l'export `GET /api/v1/dossiers/{id}/export/module1` joint automatiquement toutes les captures horodatées (documents `source=preuve-langue`) en annexe (`build_module1_pdf(dossier, proof_images)` — titre, légende par capture, image intégrée). Dossier complet en un seul fichier. Vérifié : PDF 9 pages, annexe dès page 3, 7 captures intégrées (rendu visuel OK).
- **Guide « questions restantes »** à l'étape Révision de l'entrevue guidée : calcul en direct des champs vides (respect des `showIf`, tableaux exclus) → bloc `m1-remaining` avec compteur + liste (section · libellé) + bouton « Aller » vers la section, ou `m1-remaining-complete` si tout est rempli. Vérifié : compteur/items/navigation/export 200 (le compteur est recalculé en direct sur `values`).
- UX : marquer « modifications non enregistrées » après un auto-fetch (sinon données REQ perdues si l'utilisateur quitte sans enregistrer).
- Design : remplacer les inputs date natifs (att_date, « date limite légale ») par le Calendar shadcn au format jj/mm/aaaa ; contraste du panneau REQ.
- Paiements Stripe (PRO/SOLO) — toujours P0 en attente.

## Implémenté (2026-06 — itération 12, Amorce mobile Phase 1 : couplage QR + entrevue vocale)
- **Approche légère native** (uploads HTTP + clé Emergent, aucune dépendance externe).
- **Couplage QR** : onglet « Amorce (mobile) » du dossier → bouton « Générer un lien QR » (`POST /api/v1/dossiers/{id}/amorce/session`). Jeton **haute entropie** (`secrets.token_urlsafe(32)`), expiration **30 min**, **invalidé dès la complétion**, révocable (`.../session/revoke`), une seule session active par dossier. Panneau `AmorcePanel.jsx` : QR (`qrcode.react`), lien, compte à rebours, **polling temps réel ~4 s** de l'état (réponses/photos/déclaration).
- **Page mobile publique** `/m/:sessionId` (`MobileAmorce.jsx`, aucun login, axios public) : capture **photos** par 7 catégories (Façade, Enseigne, Affichage intérieur, Poste de travail/écran, Offre d'emploi affichée — avec case explicite « aucune offre active », Documents, Autre) et **5 questions vocales** (texte exact fourni : NEQ, site web [facultatif], employés QC, % CA QC/hors QC [approx.], établissements QC). **Retry réseau** (3 tentatives) sur chaque envoi photo/audio.
- **Transcription + traduction** (`amorce.py`) : Whisper `whisper-1` transcrit dans la **langue parlée** (verbose_json → langue détectée), GPT 5.4 **traduit/normalise en français** ; **audio original conservé** comme document du dossier. Photos/audio joints au dossier (`documents` source=`amorce-photo` / `amorce-audio`).
- **Audit** : ouverture de session et complétion journalisées dans le journal d'audit du dossier.
- Vérifié : backend curl (session CRUD, info publique, photo, déclaration, transcription réelle EN→FR et FR→FR corrects) ; testing agent frontend **100 % (7/7 flux)** — génération QR, page mobile sans redirection /login, upload photo + compteur, déclaration, polling bureau, révocation, régénération.

## Prochaines tâches
- **Phase 2 — Tableaux de bord et indices (P0)** : écran d'ouverture du dossier montrant 3 indices (Francisabilité, Conformité, Risque) + diagnostic EP à 3 états, calculés à partir des données de l'Amorce ; formulaire Module 1 complet derrière un bouton « Compléter le dossier ». À tester isolément (partie la plus délicate).
- Réutiliser le patron accepter/refuser (WebEnrichPanel) pour valider les réponses vocales transcrites lors de leur report dans le formulaire.
- Paiements Stripe (PRO/SOLO) — P0.

## Implémenté (2026-06 — itération 13, validation des thèmes A1–A4)
- Textes de loi confirmés (LégisQuébec, Loi 96) insérés tels quels et `texte_loi_valide=true` pour **A1 (art. 41), A2 (art. 41(1°) et 42), A3 (art. 50.1), A4 (art. 46 et 46.1)** — s'ajoutent à A5 (art. 58) déjà validé. Le moteur peut désormais qualifier « non conforme » pour A1 à A5 ; B1–B9 (art. 141) restent au statut prudent « à valider ».
- A1 : `note_portee` distincte du `texte_loi` (le par. 4° est limitatif ; ni l'oral ni les « outils de travail » ne sont couverts par l'article — ces éléments relèvent du `libelle_oqlf`, jamais fusionnés dans `texte_loi`).
- Champs de référence externe renseignés (external_citation, reference_date 2025-06-01, retrieved_at). Vérifié : `GET /api/v1/catalogue/themes` retourne A1–A5 validés + note_portee A1.

## Implémenté (2026-06 — itération 14, report vocal → Module 1)
- Bouton « Reporter l'entrevue vocale » (Module 1, `module1-amorce-report`) : `GET /api/v1/dossiers/{id}/amorce/proposals` récupère la dernière session d'amorce ayant des réponses et mappe chaque question vers la clé exacte du schéma Module 1 (q1→s1.neq, q2→s1.sites_web, q3→s4.employes_quebec, q4→s3.pct_ca, q5→s4.etablissements) avec **extraction structurée** (NEQ 9-10 chiffres, entier, pourcentage QC = 1er nombre, URL/domaine).
- Réutilise le **patron accepter/refuser** (`WebEnrichPanel`, nouvelles props title/subtitle) : source « entrevue vocale (amorce) » + note affichant la langue détectée et la transcription française. Seuls les champs acceptés remplissent le Module 1.
- Vérifié : backend curl (proposals corrects : employés 40, %CA QC 70 depuis audio EN traduit) + testing agent frontend **100 %** (ouverture panneau, titre correct, refuser+appliquer, régression titre recherche Web OK).

## Implémenté (2026-06 — itération 15, indépendance des intégrations Emergent / pré-migration Railway)
- **Suppression de `emergentintegrations`** (retiré de requirements.txt) → le build ne dépend plus de l'index privé Emergent.
- **LLM en direct (SDK `openai`)** : `amorce.py`, `analysis.py`, `enrichment.py` utilisent `AsyncOpenAI` (`chat.completions.create` + `audio.transcriptions.create`, modèle `gpt-5.4` via `OPENAI_MODEL`, `whisper-1`). Comportement identique (transcription langue parlée → traduction FR, principe de prudence conservé, audio original conservé). Dégradation gracieuse si erreur (audio conservé + avertissement).
- **Courriels via API Resend en direct** (`mailer.py` → `https://api.resend.com/emails`, `RESEND_API_KEY`) au lieu du proxy Emergent. Gabarit/garde-fous anti-hameçonnage inchangés. **Vérifié** : envoi réel réussi (id retourné) vers l'adresse titulaire.
- **Stockage à double backend** (`storage.py`) : S3/compatible (AWS S3 ou Cloudflare R2 via `boto3`) dès que `S3_BUCKET`+`S3_ACCESS_KEY`+`S3_SECRET_KEY` sont définis ; sinon **repli** proxy Emergent (actif en prévisualisation). Retry/backoff conservé. Aller-retour put/get vérifié.
- Nouvelles variables : `OPENAI_API_KEY`, `OPENAI_MODEL`, `RESEND_API_KEY`, `EMAIL_FROM`, `S3_BUCKET`/`S3_REGION`/`S3_ACCESS_KEY`/`S3_SECRET_KEY`/`S3_ENDPOINT_URL`. Documentées dans `backend/.env.example`.
- Tests pytest : **98/98 verts** avec la clé OpenAI directe (crédits ajoutés) et le domaine Resend `dvsc.ca` vérifié (`EMAIL_FROM=conformiste@dvsc.ca`, envoi réel vers destinataire non-titulaire confirmé). `test_themes_have_external_fields` (A1–A5 validés / B1–B9 prudents), `test_req_lookup` (NEQ non numérique → 422), et les assertions de prudence (A1–A5 peuvent être « non conforme », B* restent « à valider ») mis à jour ; `test_cron_idempotent` rendu auto-suffisant. Stockage S3/R2 prêt (attend des identifiants), repli Emergent conservé pour l'instant comme convenu.

## Implémenté (2026-06 — itération 16, Phase 2 : Aperçu du diagnostic)
- Nouvel onglet **« Aperçu du diagnostic »** (1re position, actif par défaut) du dossier — `GET /api/v1/dossiers/{id}/diagnostic` (`diagnostic.py`), calcul déterministe à partir du Module 1 avec **repli sur l'amorce** (fusion des réponses de toutes les sessions, la plus récente prime).
- **Diagnostic EP (Entente particulière, art. 144)** — 3 états neutres (badge indigo, pas de couleur « problème ») : *Non admissible* / *Potentiellement admissible* / *À déterminer*. Règle : > 50 % de revenus hors Québec (déterminant) **combiné** à des activités/personnel hors Québec (établissements ou siège hors QC). Pas de zone grise ; conditions affichées avec coche/absence/tiret.
- **Francisabilité** (pas de jauge) : % revenus **hors Québec** positionné de façon **neutre** vs repère 50 %, + liste de facteurs contextuels (art. 142) non fusionnés (CA, clientèle, fournisseurs, achats hors QC, établissements hors QC), + badge EP.
- **Conformité** (bandes vert/ambre/rouge + **état neutre « Non évalué »** si couverture 0, pour ne pas induire une fausse conformité) : basée sur la langue de l'affichage public, du site web/médias sociaux, des logiciels et de l'étiquetage. Vert = tout en français · Jaune = ≥ 1 non conforme · Rouge = ≥ 3. Couverture « X évalués sur 4 » affichée.
- **Risque** (Faible/Modéré/Élevé) : score combinant conformité + assujettissement (employés ≥ 25 / ≥ 100) + proximité/dépassement de l'échéance légale.
- Bandeau **« Estimation indicative — à valider par un professionnel »** partout. Bouton **« Compléter le dossier »** → onglet Module 1.
- Vérifié : backend curl (EP non admissible/potentiellement admissible, bandes vert/jaune/rouge/non_evalue) + testing agent **100 % backend & frontend** (onglet par défaut, cohérence UI↔API, navigation bouton).

## Ordre convenu pour la suite (demande utilisateur)
1. ✅ Report vocal → Module 1 (itération 14).
2. ✅ Phase 2 — indices + diagnostic EP (itération 16).

## Implémenté (2026-06 — itération 17, Conformité enrichie)
- Les 4 éléments de conformité sont désormais alimentés **automatiquement** par les signaux terrain, qui **priment sur le Module 1** :
  - **Affichage public** : photos de l'amorce (façade/enseigne/affichage intérieur) **auto-analysées en tâche de fond** (`BackgroundTasks` → `_analyze_and_store`) via la vision LLM.
  - **Langue des logiciels** : photo « poste de travail » de l'amorce (auto-analysée).
  - **Site web et médias sociaux** : détection de langue persistée sur les documents `preuve-langue` (`lang`/`is_french`/`ev_kind`).
  - **Étiquetage** : repli Module 1 (`s8.e_inscriptions`).
- `diagnostic.derive_conformite_signals(docs)` mappe documents → statuts ; `compute_conformite(m1, signals)` affiche la **source** de chaque verdict. Vérifié bout-en-bout (photo façade anglaise → affichage « non conforme (photos de l'amorce) », bande jaune).

## Implémenté (2026-06 — itération 18, validation des thèmes B1–B9 / art. 141)
- Textes de loi de **l'article 141** (chapeau + paragraphes 1° à 9°, fournis par le client) insérés dans B1…B9 avec `texte_loi_valide=True` → le moteur peut désormais rendre « non conforme » sur A1–A5 **et** B1–B9 (tous les thèmes du catalogue sont validés).
- **`note_portee` commune** (art. 141) : le but est la généralisation du français ; l'article énumère les MOYENS ; objectif à pondérer, obligation de moyens et non de résultat absolu.
- Champs de référence renseignés (external_citation art. 141, reference_date 2022-06-01). Tests pytest mis à jour (prudence pour tous thèmes validés, `test_themes_have_external_fields` rendu dynamique, `test_cron_idempotent` déterministe par stabilisation) — **98/98 verts**.

## Implémenté (2026-06 — itération 19, Segmentation par taille : Régime A / Régime B)
- **Écran d'entrée AVANT connexion** (`SizeGate.jsx` à `/`, l'ancien Welcome passe à `/welcome`) : demande le nombre d'employés au Québec (3 choix : moins de 25 / 25-99 / 100+) avant même le choix SOLO/PRO. La taille est propagée en state jusqu'à `/register`. `Welcome` redirige vers `/` si aucune taille (bannière `welcome-regime-banner`, lien « Modifier »).
- **Le régime s'attache au DOSSIER** (`regime_from`) : `moins_25 → A`, `25_99`/`100_plus` → B. Dossier SOLO auto-créé à l'inscription et dossiers PRO (`Dashboard` → `dossier-taille-select`) portent `regime`/`taille`. Régime A → `stages=[]` (aucun pipeline).
- **Catalogue Régime A — obligations universelles U1–U18** (`catalogue.py UNIVERSAL_THEMES`, `themes_for_regime`) : textes LégisQuébec insérés, `texte_loi_valide=True` dès la création (sauf U17 art. 54 / U18 art. 55.1, marginaux, non prioritaires). U1/U2/U6/U8/U15 = partagés avec A1/A2/A4/A3/A5 (même texte légal, `shared_ref`). `GET /catalogue/themes?regime=A|B`.
- **Tableau de bord Régime A** (`RegimeAConformite.jsx`) : liste des 18 thèmes U avec statut (conforme/à valider/non conforme/non évalué) dérivé du plan de correction, texte de loi dépliable, bouton vers l'onglet Analyse. `DossierDetail` branche sur `isRegimeA` : onglets Conformité (défaut) / Amorce / Analyse / Journal ; PAS de pipeline, diagnostic EP, Module 1, Module 2.
- **Moteur d'analyse conscient du régime** : `_analyze_and_store` et `analyze_document` consultent `themes_for_regime(dossier.regime)`. `theme_by_id` cherche dans A/B + U.
- **Amorce mobile adaptée Régime A** (`amorce.questions_for_regime`/`photo_categories_for_regime`) : 3 questions vocales (NEQ, site, employés) sans % CA hors QC ni établissements ; photos façade/enseigne/affichage intérieur/produits-emballages/menus/factures/autre. Auto-analyse en tâche de fond élargie (`AMORCE_ANALYZE_CATS`).
- Régime B (25+) inchangé (non-régression validée). Vérifié : pytest 98/98 + `test_segmentation_regime.py` 9/9 + testing agent frontend 100 % (SizeGate, Welcome A/B, Register A/B, DossierDetail A/B, badge Dashboard PRO, amorce mobile A). Aucun bug.

## Implémenté (2026-06 — itération 20, Rapport PDF Régime A · Comité visible · Résumé hebdomadaire)
- **Rapport PDF Régime A** (`pdf_export.build_regime_a_pdf`, `GET /dossiers/{id}/export/regime-a`) : liste les 18 obligations universelles U1–U18 avec statut (Non évalué / À valider / Non conforme), texte de loi et constats issus de l'analyse. Bouton `regimea-export-pdf` dans `RegimeAConformite.jsx`.
- **Distinction comité 25-99 vs 100+** : badge visible dans l'en-tête du dossier Régime B (`regime-b-comite-badge` : « Comité de francisation requis · 100 employés et plus » vs « Sans comité · 25 à 99 employés ») et sur chaque ligne du tableau de bord PRO (`dossier-{id}-comite`).
- **Résumé hebdomadaire PRO** (`generate_weekly_summary`, `POST /cron/weekly-summary`, cron `resume-hebdo` lundi 12:00 UTC dans `.emergent/crons.yml`) : un courriel par consultant PRO listant les échéances d'analyse dans les 30 jours ou en retard de tout son portefeuille (`mailer.send_weekly_summary_email`, scan anti-phishing OK). Endpoint sécurisé par `WEBHOOK_CRON_SECRET`, travail en tâche de fond.
- Vérifié : endpoints curl (PDF 200 %PDF-, cron 200 accepted, 401 sur mauvais secret), captures Régime A (bouton PDF) et Régime B (badge comité).

## Implémenté (2026-06 — itération 21, Parcours PME Régime A < 25 employés)
- **Écran explicatif pré-connexion** (`RegimeAIntro.jsx`, route `/parcours-pme`) : atteint quand l'utilisateur choisit « Moins de 25 employés » sur `SizeGate`. Explique que la PME n'est pas suivie par l'Office **sauf plainte**, présente les 3 étapes du parcours et **capture le nombre exact d'employés** (0–24).
- **Parcours guidé post-connexion Régime A** (`ParcoursAStepper.jsx`) : Étape 1 Obligations universelles (U1–U18) · Étape 2 Déclaration au REQ (requise si ≥ 5 employés) · Étape 3 Traitement d'une plainte (désactivé, « à venir »). Onglets `tab-conformite`, `tab-req`, amorce, analyse, journal, `tab-plainte` (disabled).
- **Module Déclaration REQ** (`RegimeAReq.jsx`, `PUT /dossiers/{id}/req-declaration`) : champ pour consigner le nombre d'employés ne pouvant communiquer en français, proportion calculée (aide-mémoire, sans soumission au REQ). Affiché uniquement si ≥ 5 employés ; sinon « non applicable ». Stocké dans `dossier.req_declaration`.
- **Cadre légal** (`catalogue.REGIME_A_LEGAL_FRAMEWORK`, `GET /catalogue/regime-a-framework`) : art. 149, 150, 151, 152.1 (Charte) + art. 33, 10° (P‑44.1), `texte_loi_valide=true`, textes dépliables dans l'onglet Déclaration REQ.
- **Nombre exact d'employés** capturé : `RegisterIn.nb_employes` (SOLO) et champ existant du dialogue PRO. `enrich_dossier` calcule `req_declaration_requise = regime A et nb_employes ≥ 5`. En-tête du dossier : badge « Parcours PME · N employés » + « Déclaration REQ requise/enregistrée ».
- Vérifié : pytest 98/98 + segmentation 14/14 (dont 5 nouveaux tests parcours PME), captures Régime A (stepper, onglet REQ, cadre légal). Le **traitement d'une plainte reste pour une itération ultérieure** (placeholder).

## Implémenté (2026-06 — itération 22, Traitement d'une plainte — étape 3 du parcours PME)
- **Module « Traitement d'une plainte »** (`PlaintePanel.jsx`, onglet `tab-plainte`, Régime A uniquement) : suivi d'**une seule plainte par dossier** de la communication initiale jusqu'à la résolution.
- **9 étapes** (`PLAINTE_STAGES`) : Communication initiale (visite d'inspecteur/lettre) → Analyse par l'Office → Demande de correction → Négociation de l'échéancier → Pré-avis d'ordonnance → Ordonnance → Contestation au TAQ (30 j) → Exécution/référé au Procureur général → Résolution. Chaque étape : statut, date, échéance, note, **journal d'échanges**, **pièces jointes** (upload via `?category=plainte:<étape>`).
- **Alerte inspecteur** proéminente : exiger la carte d'identité ; tout refus = entrave = amende automatique ; un inspecteur n'est pas un conseiller.
- **Endpoints** : `POST /dossiers/{id}/plainte` (ouvre, refuse le Régime B → 400), `PATCH /dossiers/{id}/plainte` (référence OQLF, type communication, résolution, clôture), `PATCH /dossiers/{id}/plainte/stage/{key}`. `enrich_dossier` calcule `plainte_ouverte` / `plainte_echeance` / `plainte_jours` / `plainte_urgence`.
- **Échéances de plainte** intégrées aux **rappels** (`generate_reminders` : notifications + courriels `plainte_j7/j30/retard`) et au **résumé hebdomadaire** PRO. Stepper étape 3 activé, reflète l'état de la plainte.
- Régime B (25+) exclu volontairement : la plainte y passe par une mesure de francisation via le conseiller (hors périmètre).
- Vérifié : pytest 98/98 + segmentation 17/17 (3 nouveaux tests plainte), curl (ouverture 9 étapes, échéance J-5 → urgence critical, refus Régime B 400), capture du module plainte.

## Implémenté (2026-06 — itération 23, Modèles de lettre + Export PDF de la plainte)
- **Modèles de lettre à l'OQLF** (`GET /dossiers/{id}/plainte/lettre?type=`, carte `plainte-letters`) : 3 modèles pré-remplis (accusé de réception, demande de délai, correctif proposé) avec nom/NEQ/référence/date, éditables + copie presse-papier.
- **Export PDF du dossier de plainte** (`pdf_export.build_plainte_pdf`, `GET /dossiers/{id}/export/plainte`, bouton `plainte-export-pdf`) : dossier horodaté = métadonnées + chronologie des 9 étapes (statut, dates, notes), **journal d'échanges** et **pièces jointes** listées par étape — preuve de suivi.
- Vérifié : curl (lettre générée, PDF 200 %PDF-, type invalide → 400), AST backend OK.

## Implémenté (2026-06 — itération 24, Refonte parcours PME : hub A/B + inscription directe)
- **Plus de page SOLO/PRO pour les < 25** : SizeGate « Moins de 25 » → `/parcours-pme` (saisie du nombre exact) → **inscription directe** (`Register` sans sélecteur SOLO/PRO, compte SOLO implicite). La page SOLO/PRO reste réservée aux 25+.
- **Hub A/B** (`RegimeAHub.jsx`) = accueil du dossier Régime A : deux cartes **Parcours A — Mise en conformité** et **Parcours B — Traitement d'une plainte**, toujours accessibles ; « Retour au choix » après chaque parcours. Outils secondaires : Amorce mobile, Analyse documentaire, Journal d'audit.
- **Parcours A** (`ParcoursAElements.jsx`) = **une étape par élément** : U1 à U18 (18) + **Déclaration REQ** en 19e (uniquement si ≥ 5 employés → sinon 18). Chaque élément : statut (conforme/à valider/non conforme/sans objet/non évalué), note, **preuve jointe**, texte de loi, et constats auto-détectés par l'analyse. Progression `X/total` affichée. `PATCH /dossiers/{id}/parcours-a/element/{code}` ; `enrich_dossier` calcule `parcours_a_total` / `parcours_a_traites`.
- **Parcours B** = module de plainte existant (9 étapes, lettres, PDF) rebranché dans le hub. La « Déclaration REQ » n'est plus un parcours séparé mais une étape du Parcours A.
- Vérifié : flux UI complet (/ → PME → register sans SOLO/PRO → hub A/B → Parcours A), curl (total=19, patch élément incrémente, Régime B → 400), pytest segmentation.

## Implémenté (2026-06 — itération 25, Kanban de traitement d'une plainte + modèle « Mesure »)
- **Unité « Mesure »** (partagée Parcours A/B) : `dossier.mesures[]` avec titre, élément lié, description, moyen, responsable, date début/échéance, `incontournable`, statut, validité (fondée/non fondée), gravité, checklist de preuves, journal (append-only), pièces (documents `mesure:<id>`). Endpoints `POST/PATCH/DELETE /dossiers/{id}/mesures`.
- **Parcours B → Kanban** (`KanbanBoard.jsx`) : 6 colonnes OQLF (Réception & Analyse · En attente de réponse OQLF · Correctif en cours · Validation de la preuve · Notification envoyée · Fermé/Conforme). Cartes = mesures ; déplacement par menu déroulant ; date butoir rouge à J‑10/J‑5 ; pastilles gravité/validité ; alerte inspecteur ; checklist + preuves + journal traçable. Remplace l'ancien PlaintePanel dans le hub.
- Vérifié : curl CRUD (create/move/echange/incontournable/delete) + capture Kanban.
- **À VENIR (prochain tour)** : Parcours A → vue **Gantt** (barres par élément U1–U19). **Rappels/résumé hebdo des échéances de mesures : en attente d'approbation utilisateur.**

## Prochaines tâches (backlog)
- **Stripe Payments (P0)** : abonnements PRO/SOLO (clé env disponible dans le pod).
- **Module 2 (P1)** : autres formulaires/modules.
- **Storage S3/R2 (P1)** : migration depuis le repli Emergent quand identifiants fournis.
- **Préférences courriel (P2)**, **Résumé hebdomadaire portefeuille PRO (P2)**.

## Implémenté (2026-06 — itération 26, Gantt Parcours A + cartes Kanban enrichies)
- **Vue Gantt du Parcours A** (`GanttParcoursA.jsx`) : bascule Liste/Gantt dans le Hub Régime A (`RegimeAHub.jsx`, `parcoursa-view-liste`/`parcoursa-view-gantt`). Barres temporelles pour les 18 obligations universelles U1–U18 + Déclaration REQ (si ≥ 5 employés). **Échelle par semaines**, ligne verticale « aujourd'hui », barres **incontournables en rouge** (ring), barres **provisoires** (pointillés) à échéance **+3 mois par défaut** si non planifié. Édition des dates + drapeau incontournable par élément.
- **Backend** : `ParcoursAElementIn` étendu (`date_debut`, `date_echeance`, `incontournable`), persistés dans `parcours_a_elements[code]` via `PATCH /dossiers/{id}/parcours-a/element/{code}`.
- **Cartes Kanban enrichies** (`KanbanBoard.jsx` → `LettersProofs`) : 3 modèles de lettre OQLF (accusé de réception, demande de délai, correctifs proposés) rebranchés dans chaque carte via `GET /dossiers/{id}/plainte/lettre?type=`, éditables + **copie robuste** (fallback `execCommand` si Clipboard API refusée) ; **guide des preuves acceptées** (8 items, dépliable).
- Vérifié : backend curl (PATCH element dates+incontournable persiste) + testing agent frontend (iteration_19, 95 % → bug copie corrigé et re-vérifié en self-test : toast OK, éditeur non cassé).
- **Rappels/alertes SLA sur les Mesures : toujours en attente d'approbation utilisateur (non activés).**

## Implémenté (2026-06 — itération 27, Gantt francisation Régime B + GanttGrid partagé)
- **Composant Gantt partagé** (`GanttGrid.jsx`) : grille temporelle générique (semaines, ligne « aujourd'hui », barres, colonne libellés) + helpers `effectiveDates`/`isoDate`/`startOfToday`. `GanttParcoursA.jsx` refactoré pour l'utiliser (non-régression validée).
- **Gantt des mesures de francisation (Régime B SOLO/PRO)** (`GanttFrancisation.jsx`) : bascule Programme ↔ Gantt dans l'onglet Module 2 (`module2-view-programme`/`module2-view-gantt`). Une barre par `module2_mesures`, couleur selon statut RMO (à faire=gris, en cours=bleu, complétée=vert, reportée=ambre), **incontournable en rouge**, échéance provisoire **+3 mois par défaut**. Édition début/échéance/incontournable persistée via `PATCH /dossiers/{id}/module2` (champ début=`date_debut`, échéance=`echeance`). État vide guidant vers l'onglet Programme.
- Vérifié : testing agent frontend **100 %** (iteration_20) — rendu, couleurs, édition + persistance après reload, bascule, + non-régression Gantt Parcours A. Aucun bug.
- **Rappels/alertes SLA : toujours non activés (en attente d'approbation utilisateur).**

## Implémenté (2026-06 — itération 28, Export Gantt PDF/PNG + Portefeuille PRO)
- **Export du diagramme de Gantt (PDF + PNG)** : bouton `ExportGanttButton` (PDF/PNG) dans le Gantt Parcours A (Régime A) et le Gantt francisation (Régime B, onglet Module 2). Backend `GET /dossiers/{id}/gantt/export?kind=parcours_a|francisation&format=pdf|png` — génération reportLab (paysage, page à hauteur dynamique, barres colorées par statut, incontournables en rouge, ligne aujourd'hui, échelle par semaines) + rasterisation PNG via PyMuPDF. `pdf_export.py` → `build_gantt_pdf` / `gantt_pdf_to_png`. Journalisé (audit).
- **Page Portefeuille PRO** (`PortefeuillePro.jsx`, route `/portefeuille`, PRO only, lien nav `nav-portefeuille`) — **MAQUETTE** de suivi d'ensemble des dossiers clients avec bascule **Gantt ↔ Kanban** :
  - Vue Gantt : une barre par dossier (attestation → échéance légale), couleur selon urgence (bleu > 30 j, ambre ≤ 30 j, rouge critique ≤ 7 j), clic → ouvre le dossier.
  - Vue Kanban : colonnes = 8 étapes du pipeline de francisation, cartes = dossiers placés à leur étape courante, clic → ouvre le dossier.
  - KPI (dossiers, échéances critiques) + invite à choisir la vue principale préférée.
- Vérifié : testing agent frontend **100 %** (iteration_21) — exports PDF/PNG (200 + toasts) sur les deux Gantt, portefeuille Gantt/Kanban + navigation, garde ProOnly (SOLO redirigé), non-régression des Gantt. Backend exports validés par curl (PDF/PNG valides).
- **Rappels/alertes SLA : toujours non activés (en attente d'approbation utilisateur).**

## À DÉCIDER (avec l'utilisateur)
- **Vue principale du Portefeuille PRO** : l'utilisateur doit indiquer sa préférence (Gantt chronologique vs Kanban par étape) pour en faire la vue par défaut / l'affiner.

## Refonte Parcours A — PHASE 1 (2026-06, itération 29)
- **Démarrage par le NEQ** : nouvel onglet « Profil / démarrage » (`ParcoursAProfil.jsx`) en tête du Parcours A. Recherche NEQ → pré-remplit nom légal + marques de commerce (source **simulée** `req_lookup.simulate_req` ; à remplacer par la vraie source REQ / un CSV fourni par l'utilisateur).
- **Questionnaire préalable qui filtre les obligations** : syndicat, vend des produits, vend des jouets/jeux, immobilier résidentiel. Gates (catalogue.py) : U3/U7/U8=syndicat, U10/U11/U14=produits, U17=jouets, U18=immo. U4/U5 = **rappels informatifs** (protections « après les faits », sans saisie ni diagnostic).
- **Effectifs & REQ préparatoire** : nb total d'employés + nb pouvant s'exprimer en français → proportion NE pouvant PAS communiquer en français, **reportée** dans la déclaration REQ (préremplissage), mais **aucun envoi sans consentement** (bouton d'enregistrement explicite conservé).
- **Backend** : `ParcoursAProfilIn` + `PUT /dossiers/{id}/parcours-a/profil` ; `enrich_dossier` expose `parcours_a_applicable` / `parcours_a_info_only` ; `nb_employes_quebec`, `neq`, `nom_entreprise` mis à jour depuis le profil. Liste et Gantt filtrés sur les obligations applicables.
- Vérifié : testing agent frontend **100 %** (iteration_22) — NEQ (valide/invalide), % 3/8=37,5 %, filtrage bidirectionnel (syndicat/produits/jouets/immo), rappels U4/U5, REQ préremplie+consentement, Gantt filtré, non-régression édition U1.

## Refonte Parcours A — PHASE 2 (À FAIRE, prochaine étape)
- Remplacer, pour chaque obligation applicable, le duo « statut Non évalué + note justificative » par une **saisie de données guidée + téléversement de fichiers/photos**, à partir desquels **CONFORMISTE produit un diagnostic** (constat + actions correctives) via l'analyse IA (OpenAI direct).

## Refonte Parcours A — PHASE 2 (2026-06, itération 30) — PILOTE U6
- **Outil d'évaluation U6** (exigence d'une autre langue, art. 46/46.1) accessible depuis la carte U6 (`ParcoursAElements` → bouton `parcoursa-open-u6` → `U6Tool.jsx`). Par **poste/catégorie d'emploi** (ajout/édition/suppression), en 5 sections :
  - **0** Identification (titre, postes visés/total, langues exigées).
  - **0bis** Description de tâches — **bibliothèque intégrée** de 3 fiches-types CNP (caissier, commis aux ventes, préposé au service à la clientèle) sélectionnables et éditables, chaque tâche avec case « nécessite une autre langue ». Avertissement si aucune tâche.
  - **1** Besoins réels (interlocuteurs, fréquence, % non-francophones — présenté comme fait, pas un seuil, nature des tâches, téléversement de preuves).
  - **2** Insuffisance des connaissances (inventaire, vérification formelle/informelle ; avertissement si informelle).
  - **3** Réduction des postes + **garde-fou art. 40.1 toujours visible** + case de confirmation (avertissement si non cochée, jamais bloquant).
  - **4** Motif d'offre (art. 46 al. 2) avec **aide IA de rédaction** (`u6_ai.draft_motif`, OpenAI direct gpt-5.4) à partir des faits documentés.
- **RÈGLE CLÉ respectée** : aucun verdict/score de conformité automatique. L'outil DOCUMENTE ; l'enregistrement marque U6 « À valider » (jamais « Conforme » auto). Export PDF « dossier de démarche documentée » (garde-fous + avertissements inclus).
- **Backend** : `GET /catalogue/u6/cnp-library`, `GET/PUT /dossiers/{id}/parcours-a/u6`, `POST .../u6/motif-draft`, `GET .../u6/pdf?poste_id=` ; `pdf_export.build_u6_pdf` ; `catalogue.CNP_TASK_LIBRARY`.
- **Correctif au passage** : le décorateur `@api.get(.../export/regime-a)` avait été supprimé par erreur en Phase 1 — restauré.
- Vérifié : testing agent frontend **100 %** (iteration_23) — 5 sections, bibliothèque CNP, garde-fous non bloquants, IA motif factuelle sans verdict, persistance, PDF 200, statut « À valider », non-régression (Profil/Liste/Gantt/Parcours B). PDF rendu vérifié visuellement.

## Refonte Parcours A — PHASE 2 (suite, à venir)
- Décliner le même principe (saisie structurée + preuves, sans verdict) aux autres obligations applicables (au-delà de U6).

## À VENIR (convenu avec l'utilisateur)
- **Vue d'ensemble PRO multi-dossiers** (Gantt portefeuille vs Kanban) : à rediscuter avec l'utilisateur — lui présenter une maquette Gantt vs Kanban pour suivre l'ensemble des dossiers clients d'un consultant PRO.
- **Rappels échéances (mesures + Gantt)** : proposés à l'utilisateur (alertes in-app + courriel hebdo) — en attente de « oui ».
