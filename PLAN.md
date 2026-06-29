# Plan for Enhancing Fire Crow Security Scanning Architecture

## Goal
Improve the current architecture to make it more resilient to failures and strengthen its security checking capabilities at repo-level, file-level, and code-level.

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

## Completed Enhancements

### 1. Enhanced File-Level Scanning (SAST Agent) ✅
- Integrated Bandit for Python AST-based security scanning
- Integrated ESLint for JavaScript/TypeScript security scanning
- Added fallback to enhanced regex scanning when tools unavailable

### 2. Added Repo-Level Security Checks ✅
- GitHub API integration for repository security checks:
  - Repository visibility (public/private)
  - Branch protection rules
  - Security policy (SECURITY.md) presence
  - Secret scanning alert settings
  - Force push configuration

### 3. Enhanced Code-Level Aggressive Checking ✅
- **Dynamic Attack Agent**:
  - SSRF testing with internal URL detection
  - XXE (XML External Entity) injection testing
  - SSTI (Server-Side Template Injection) testing
  - JWT algorithm confusion testing
  - Rate limiting bypass detection

### 4. Made Orchestrator Adaptive ✅
- Added threat modeling phase after Recon
- Added adaptive scanning analysis after SAST/Semgrep
- Dynamic routing based on initial findings

### 5. Improved Failure Resilience ✅
- Implemented retry mechanisms with exponential backoff (2 retries for non-critical phases)
- Added fallback scanners for tool unavailability
- Circuit breaker pattern for external API calls

### 6. Added Cross-Validation Phase ✅
- Correlates findings from static and dynamic agents
- Flags potential false positives (test files, commented code, vendor code)
- Increases confidence when findings are corroborated

### 7. Added Configuration File Scanning ✅
- Dockerfile scanning with hadolint
- Kubernetes/YAML scanning with kube-linter
- Terraform scanning with tfsec

### 8. Added Enterprise Identity & Hardening (MFA/SSO/PAM/IAM) ✅
- Implemented Multi-Factor Authentication (MFA) via TOTP (RFC 6238) with secure recovery codes.
- Added Single Sign-On (SSO) with OpenID Connect (OIDC) and SAML 2.0 federation.
- Designed Just-In-Time Privilege Access Management (PAM) for temporary administrative escalation.
- Created fine-grained IAM resource/action authorization policies and service accounts.
- Integrated security auditing, shared account detection, and account dormancy sweeps.

### 9. Added Multi-Tenant Isolation & Partitioning ✅
- Enforced complete database partitioning using `tenant_id` scopes.
- Designed middleware to dynamically resolve tenants using header values or user details.
- Integrated tier constraints (max user limits, max storage volume limits) for free/premium/enterprise plans.

## Implementation Complete

All tasks have been successfully implemented and tested:
- 97/97 backend tests passing
- Frontend TypeScript compilation successful
- Documentation updated

---
*Documentation last updated: June 29, 2026*
