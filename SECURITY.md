# Security Policy

## Authorized Use Only

Fire Crow is intended for authorization-only security review workflows. Do not use this repository, its code, or derived deployments to target systems you do not own or lack explicit permission to test.

## Reporting A Vulnerability

Use a private security contact before opening a public issue.

Current placeholder contact:

- `security@example.com`

Replace that address with the real reporting channel before relying on this file operationally.

## Do Not Submit Real Secrets

- Do not paste production credentials, access tokens, private keys, or customer data into GitHub issues, PRs, or test fixtures.
- If sensitive data was committed accidentally, rotate it first and then report the incident privately.

## Supported Branch

- `main`

## Responsible Disclosure Expectations

- provide reproduction steps
- describe impact clearly
- avoid public disclosure until maintainers have had a reasonable chance to respond
- do not escalate access, persistence, or data extraction beyond what is required to prove the issue

## No Abuse Or Malware Guidance

- Do not submit exploit kits, malware payloads, or destructive automation as "tests."
- Defensive proof-of-concept material should stay minimal, bounded, and safe to review.

## Deployment Security Hardening Controls

To harden Fire Crow production deployments, configure and leverage the following built-in security controls:

- **Multi-Factor Authentication (MFA)**: Enforce TOTP MFA for administrative accounts by setting `MFA_ENFORCE_FOR_ADMINS=true`. Administrative routes are blocked unless MFA is verified.
- **Single Sign-On (SSO) Federation**: Connect your enterprise Identity Provider using OpenID Connect (OIDC) or SAML 2.0. Limit access to trusted organizational email domains by configuring SSO provider domain constraints.
- **Just-In-Time Escalation (PAM)**: Assign regular engineering privileges and require engineers to request temporary administrative roles for specific tasks using the `/pam` workflow. Active grants expire automatically.
- **IAM Policies**: Restrict user access by writing fine-grained resource and action policies to enforce the Principle of Least Privilege.
- **Dormancy & Shared Account Audits**: Run periodic cleanup scripts or query auditing endpoints to detect dormant users (inactive for 90 days) and suspicious shared credentials (accessed across more than 5 distinct IPs).

---
*Documentation last updated: June 29, 2026*
