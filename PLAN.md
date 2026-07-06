# Plan for Enhancing Fire Crow Security Scanning Architecture

## Goal
Improve the current architecture to make it more resilient to failures, strengthen its security checking capabilities, and upgrade Fire Crow to a high-performance, distributed scanner capable of conducting authorized live web security audits.

## Current State Analysis
The system uses a modular orchestrator (maestro.py) with sequential phases:
1. Recon (cloning, tech stack detection)
2. Threat Modeling
3. API Surface detection
4. Secret history scanning
5. Dependency scanning
6. SBOM generation
7. IaC scanning
8. CI/CD scanning
9. Container scanning
10. Config file scanning
11. SAST (regex, Bandit, ESLint)
12. Semgrep scanning
13. Authz/IDOR analysis
14. Sandbox provisioning
15. Network scanning
16. Dynamic attack (OWASP Top 10, SSRF, XXE, SSTI, JWT, rate limit)
17. Exploit validation
18. AI Analyzer (deterministic triage)
19. Cross-Validation
20. Scoring (CVSS assignment)
21. Attack graph building
22. Remediation planning
23. Reporting
24. GitHub MCP notification
25. Google Agent notification
26. Cleanup

## Completed Repository Audit Enhancements ✅

### 1. Enhanced File-Level Scanning (SAST Agent) ✅
- Integrated Bandit for Python AST-based security scanning
- Integrated ESLint for JavaScript/TypeScript security scanning
- Added fallback to enhanced regex scanning when tools unavailable

### 2. Added Repo-Level Security Checks ✅
- GitHub API integration for repository security checks:
  - Repository visibility (public/private), branch protection rules, security policy (SECURITY.md) presence, secret scanning alert settings, force push configuration.

### 3. Enhanced Code-Level Aggressive Checking ✅
- SSRF testing with internal URL detection, XXE (XML External Entity) injection testing, SSTI (Server-Side Template Injection) testing, JWT algorithm confusion testing, and rate limiting bypass detection.

### 4. Made Orchestrator Adaptive ✅
- Added threat modeling phase after Recon and adaptive scanning analysis after SAST/Semgrep.

### 5. Multi-Tenant Isolation & Hardening (MFA/SSO/PAM/IAM) ✅
- Implemented MFA via TOTP, SSO via OIDC & SAML 2.0, Just-In-Time PAM, fine-grained IAM resource/action authorization, service accounts, database multi-tenant isolation partitioning.

---

## Live Website Scanning & Security Upgrades Roadmap 🚀

### Phase 1: Security & Compliance (Safe Live Scanning) ✅
- [x] Implement DNS TXT Lookup Challenge (`_firecrow-challenge.domain.com`) ── **Completed**
- [x] Implement HTML Meta Tag Verification (`firecrow-verification`) ── **Completed**
- [x] Implement Well-Known File Upload verification (`/.well-known/firecrow.txt`) ── **Completed**
- [x] Create `/api/v1/verify-domain` FastAPI endpoints and models ── **Completed**
- [x] Build Frontend Verification UI inside Settings/Dashboard ── **Completed**
- [x] Implement static outbound IP pool documentation and rate limiting rules ── **Completed**

### Phase 2: System Efficiency (Asynchronous Distributed Architecture) ── **Planned**
- [ ] Integrate Redis & Celery into the docker compose environment
- [ ] Port `maestro.py` sequence phases into asynchronous Celery subtasks
- [ ] Implement live scan progress streaming via WebSocket/SSE updates

### Phase 3: Vigorous Security Detection Upgrades ── **Planned**
- [ ] Integrate OWASP ZAP API client for passive/active crawling
- [ ] Implement dynamic CMS & technology stack fingerprinting (Wappalyzer clone)
- [ ] Add advanced parameter fuzzing and tech-aware nuclei payload selectors
- [ ] Refine `attack.py` and `exploit.py` for live WAN scans (SSL handshake, redirect loops)

---
*Documentation last updated: July 7, 2026*
