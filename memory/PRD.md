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

## Ordre convenu pour la suite (demande utilisateur)
1. ✅ Report vocal (réponses Amorce transcrites) → préremplissage Module 1 via patron accepter/refuser — **FAIT** (itération 14).
2. Phase 2 — indices (Francisabilité, Conformité, Risque) + diagnostic EP 3 états.

## Implémenté (2026-06 — itération 14, report vocal → Module 1)
- Bouton « Reporter l'entrevue vocale » (Module 1, `module1-amorce-report`) : `GET /api/v1/dossiers/{id}/amorce/proposals` récupère la dernière session d'amorce ayant des réponses et mappe chaque question vers la clé exacte du schéma Module 1 (q1→s1.neq, q2→s1.sites_web, q3→s4.employes_quebec, q4→s3.pct_ca, q5→s4.etablissements) avec **extraction structurée** (NEQ 9-10 chiffres, entier, pourcentage QC = 1er nombre, URL/domaine).
- Réutilise le **patron accepter/refuser** (`WebEnrichPanel`, nouvelles props title/subtitle) : source « entrevue vocale (amorce) » + note affichant la langue détectée et la transcription française. Seuls les champs acceptés remplissent le Module 1.
- Vérifié : backend curl (proposals corrects : employés 40, %CA QC 70 depuis audio EN traduit) + testing agent frontend **100 %** (ouverture panneau, titre correct, refuser+appliquer, régression titre recherche Web OK).
