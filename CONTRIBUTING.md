# Contributing

Fire Crow is an authorization-only security audit project. Contribute in ways that keep the repository honest about what is real, optional, simulated, or still incomplete.

## Project Boundaries

- Do not expand claims in docs, UI, or policy text beyond what the code implements today.
- Do not add offensive behavior that breaks the authorization-only boundary.
- Prefer changes that improve traceability, safety, and operational clarity.

## Safe Contribution Rules

- Inspect affected source files before editing.
- Preserve tenant scoping, auth checks, redaction, and sandbox restrictions.
- Keep production and debug behavior clearly separated.

## No Hardcoding Policy

- Do not hardcode secrets, tokens, endpoints, ports, or environment-specific values.
- Wire new tunables through config or existing contract types when needed.

## Tests

- Run the smallest relevant automated checks for your change.
- For backend changes, prefer `pytest backend/tests`.
- For frontend changes, run `npm run lint` and `npm run build` in `frontend/`.
- If a check was not run, say so in the PR.

## Docs Update Requirement

- Update `README.md` and the relevant `docs/*.md` files whenever behavior, routes, config, or limitations change.
- Documentation should describe the current repository, not future aspirations.

## Commit And PR Expectations

- Keep changes scoped and reviewable.
- Note API contract changes explicitly.
- Call out security impact, migration impact, and config impact.
- If you touch backend routes or schemas, update frontend endpoint mapping docs when needed.

## No Offensive Misuse

- Do not use this repository to facilitate unauthorized scanning or abusive workflows.
- Preserve the attestation and authorization model rather than weakening it.

