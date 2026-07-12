# Fire Crow API - Backend Services

Autonomous Agentic Security Intelligence Platform Backend.

---

## Features
* **Agentic Security Auditing:** Automatically runs SAST, Dependency Analysis, Secret Git History Checks, Sandbox Exploit Validation, and correlation scoring.
* **MFA & SSO Integrations:** Built-in support for Multi-Factor Authentication (TOTP) and SSO OAuth (GitHub/Google).
* **PR Remediation Pipeline:** Auto-generates code fixes, pushes the updated fixes to a branch, and opens a Pull Request on GitHub.
* **Email Delivery:** Compiles HTML/PDF reports and emails them via Resend, Brevo, or SMTP.
* **Expo-Ready:** Standard Bearer Token support and automatic CSRF bypass for mobile client requests.

---

## Configuration & Environments

The backend uses Pydantic Settings. All variables can be configured via environment variables or a `.env` file at the root. The following configuration settings have been hardcoded as built-in default fallbacks:

### Core Server Settings
* `DEBUG`: `False` (Production mode)
* `PORT`: `8000` (FastAPI listener port)
* `SECRET_KEY`: `a7f3b8c29e4d5f6a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a`
* `FRONTEND_URL`: `https://fire-crow.onrender.com`
* `CORS_ORIGINS`: `https://fire-crow.onrender.com`
* `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: `1440` (24 hours)

### Databases & Cache
* `DATABASE_BACKEND`: `postgresql`
* `DATABASE_URL`: `postgresql://neondb_owner:npg_c6aUlVjpNeP1@ep-twilight-night-aolox43p-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
* `FIRE_CROW_MOCK_SANDBOX`: `True` (Enables mocked execution for sandbox trials)

### Integrations & Services
* `GITHUB_CLIENT_ID`: `YOUR_GITHUB_CLIENT_ID`
* `GITHUB_CLIENT_SECRET`: `YOUR_GITHUB_CLIENT_SECRET`
* `GITHUB_TOKEN`: `YOUR_GITHUB_TOKEN`
* `GOOGLE_CLIENT_ID`: `YOUR_GOOGLE_CLIENT_ID`
* `GOOGLE_CLIENT_SECRET`: `YOUR_GOOGLE_CLIENT_SECRET`
* `RESEND_API_KEY`: `YOUR_RESEND_API_KEY`
* `SENDER_EMAIL`: `onboarding@resend.dev`
* `GEMINI_API_KEY`: `YOUR_GEMINI_API_KEY`
* `GEMINI_MODEL`: `gemini-2.0-flash`

---

## Core API Endpoints

### 1. Authentication (`/api/v1/auth`)

* **POST** `/auth/register` — Registers a new user account.
* **POST** `/auth/login` — Sign in and receive a JSON TokenResponse.
* **GET** `/auth/github` — Begins GitHub OAuth loop.
* **POST** `/auth/exchange` — Exchanges short-lived OAuth codes for an access token (used in Expo).
* **POST** `/auth/logout` — Revokes the active session token.

### 2. Audits (`/api/v1/audit`)

* **POST** `/audit/submit` — Submit a GitHub repository url and branch for automated security scanning.
* **GET** `/audit/jobs` — Retrieve audit history.
* **GET** `/audit/{job_id}` — Get status and detailed findings of a specific audit job.
* **GET** `/audit/{job_id}/report` — Returns the generated HTML report or downloads the PDF report.

---

## Local Setup & Development

### 1. Install dependencies
```bash
python -m venv venv
source venv/bin/activate  # .\venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Run Database Migrations
```bash
alembic upgrade head
```

### 3. Run the Development Server
```bash
uvicorn app.main:app --reload
```

---

## Heroku Deployment

To deploy to Heroku, execute the following from the root directory:
```bash
# Push the backend directory to Heroku
git subtree push --prefix Fire-Crow-/backend heroku main
```
The included `Procfile` handles running migrations during the release phase automatically before launching `uvicorn`.

---

## Expo Mobile App Integration

When calling the API from an Expo app, use standard Bearer authorization headers:

```javascript
// Example login and token retrieval
const response = await fetch("https://fire-crow.onrender.com/api/v1/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    username: "user1",
    password: "secure_password",
    privacy_policy_accepted: true,
    privacy_policy_version: "2026-06-06"
  })
});
const data = await response.json();
const token = data.access_token; // Save in SecureStore

// Make state-changing requests using Bearer token (bypasses CSRF checks)
const submitAudit = await fetch("https://fire-crow.onrender.com/api/v1/audit/submit", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    repo_url: "https://github.com/example/repo",
    repo_branch: "main",
    authorization_scope: "authorized"
  })
});
```
