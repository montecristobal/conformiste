# CONFORMISTE — Checklist de déploiement Railway

## 1. Backend (service FastAPI) — variables d'environnement

### 🔴 Obligatoires (l'app ne démarre pas sans elles)
| Variable | Description | Exemple / valeur |
|---|---|---|
| `MONGO_URL` | URI MongoDB (plugin Railway MongoDB ou MongoDB Atlas) | `mongodb://...:27017` ou `mongodb+srv://...` |
| `DB_NAME` | Nom de la base | `conformiste` |
| `JWT_SECRET` | Secret de signature des jetons (long, aléatoire) | générer : `openssl rand -hex 32` |
| `OPENAI_API_KEY` | Clé OpenAI (GPT + Whisper) | `sk-proj-...` |
| `OPENAI_MODEL` | Modèle de chat | `gpt-5.4` |
| `RESEND_API_KEY` | Clé API Resend | `re_...` |
| `EMAIL_FROM` | Adresse expéditrice (domaine vérifié dans Resend) | `conformiste@dvsc.ca` |
| `EMAIL_FROM_NAME` | Nom affiché | `CONFORMISTE` |
| `CORS_ORIGINS` | Origines autorisées (domaine du frontend, séparées par des virgules) | `https://app.conformiste.ca` |
| `FRONTEND_URL` | URL du frontend (liens dans les courriels) | `https://app.conformiste.ca` |
| `WEBHOOK_CRON_SECRET` | Secret exigé par l'endpoint cron | générer : `openssl rand -hex 32` |

### 🟠 Compte propriétaire initial (seed au 1er démarrage)
| Variable | Exemple |
|---|---|
| `ADMIN_EMAIL` | `denis@flashcom.qc.ca` |
| `ADMIN_PASSWORD` | mot de passe fort |
| `ADMIN_NAME` | `Propriétaire` |
| `ADMIN_ACCOUNT_TYPE` | `PRO` |

### 🟡 Facultatives
| Variable | Description |
|---|---|
| `EMAIL_REPLY_TO` | Adresse de réponse (Reply-To) |

## 2. Stockage des documents/photos — CHOISIR UNE OPTION

### Option A — S3 / Cloudflare R2 (indépendance totale, recommandé pour Railway)
Dès que ces 3 variables (au moins) sont définies, le backend utilise S3 automatiquement :
| Variable | Description |
|---|---|
| `S3_BUCKET` | Nom du bucket |
| `S3_REGION` | Région (ex. `us-east-1`) |
| `S3_ACCESS_KEY` | Clé d'accès |
| `S3_SECRET_KEY` | Clé secrète |
| `S3_ENDPOINT_URL` | **Cloudflare R2 uniquement** : `https://<accountid>.r2.cloudflarestorage.com` (laisser vide pour AWS S3) |

### Option B — garder le stockage Emergent temporairement (repli)
⚠️ Ce n'est PAS une indépendance complète (le backend appelle encore le proxy Emergent) :
| Variable | Description |
|---|---|
| `EMERGENT_LLM_KEY` | Clé Emergent (init du stockage proxy) |
| `INTEGRATION_PROXY_URL` | (facultatif) URL du proxy Emergent |

## 3. Frontend (service React / build statique)
| Variable | Description | Exemple |
|---|---|---|
| `REACT_APP_BACKEND_URL` | URL publique du backend Railway (SANS `/api` final) | `https://conformiste-api.up.railway.app` |

> Rappel : le frontend appelle toujours `${REACT_APP_BACKEND_URL}/api/...`. À définir au moment du build.

## 4. Tâche planifiée (rappels J-30 / J-7 / en retard)
Emergent gérait le cron via `.emergent/crons.yml`. Sur Railway, recréer une tâche planifiée équivalente :
- **Fréquence** : tous les jours à 12:00 (`0 12 * * *`)
- **Action** : `POST {BACKEND_URL}/api/v1/cron/reminders`
- **En-tête** : `Authorization: Bearer <WEBHOOK_CRON_SECRET>`
- Outils possibles : Railway Cron, un service worker planifié, ou un cron externe (ex. cron-job.org / GitHub Actions).

## 5. Vérifications post-déploiement
- [ ] `GET {BACKEND_URL}/api/v1/catalogue/stages` → 401 (protégé) = backend up.
- [ ] Connexion avec le compte admin seedé.
- [ ] Envoi d'un courriel de rappel (domaine Resend vérifié) → destinataire reçoit le message.
- [ ] Amorce mobile : transcription + traduction FR d'une réponse vocale (crédits OpenAI OK).
- [ ] Téléversement d'une photo/document (backend de stockage choisi).
- [ ] `requirements.txt` sur `main` ne contient plus `emergentintegrations` ni `litellm` (URL Emergent).
