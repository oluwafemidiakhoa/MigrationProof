# MigrationProof — Founding Design-Partner Pilot (proposal)

**Positioning:** Independent, explainable checks for SQL Server migration acceptance. **Not** a migration service, data-recovery guarantee, compliance certificate, or proof of complete database equivalence.

## Ideal design partner

A Microsoft-focused data migration consultancy with an upcoming **nonproduction** SQL Server-to-Azure SQL or SQL Server-to-SQL Server rehearsal, a named technical sponsor, and a real sign-off pain point.

## Proposed paid offer — pricing hypothesis, not a published or validated price

**$2,500 fixed-fee, one scoped rehearsal**, subject to discovery, technical fit, security review and a signed statement of work. Do not invoice or accept sensitive data before a written scope and approval.

**Included (only after readiness gates):**
- 30-minute intake and acceptance-check selection
- Authorized, read-only collection on two approved test databases, run by customer personnel or an approved local operator
- Reconciliation of selected table metadata, exact row counts, and explicitly configured numeric aggregates
- Discrepancy register, input SHA-256 digests, HTML report and 45-minute review
- One retest of agreed checks after remediation, within a bounded pilot window

**Explicit exclusions:** production cutover approval; comprehensive row-by-row equivalence; SSIS package execution or validation; financial audit attestation; data transfer to a hosted service; remediation of the migration itself.

**Acceptance criteria:** approved environment and credentials, documented test dataset, selected tables/checks, recorded collection time, reproducible report, no unreviewed data exfiltration. Failed or incomplete checks are reported as such; never as PASS.

## Readiness gates before any paid customer assessment

1. Independently collect two test databases and demonstrate an intentionally altered numeric value with equal row counts.
2. Validate metadata types and restricted-permission visibility; incomplete scope must not report a complete PASS.
3. Enforce validated TLS, read-only least-privilege access, query timeouts and resource limits.
4. Run automated CI and independent lab integration tests; review privacy, retention and evidence handling.
5. Approve written SOW, liability boundaries, and customer-specific security terms.

Until these gates pass, offer **discovery calls and synthetic-data demos**, not an operational paid assurance service.

## Discovery interview (15 minutes)

1. Which migrations are planned over the next 90 days?
2. Who signs off that the migrated database is acceptable?
3. What evidence do they require before cutover?
4. Which validation steps are manual or regularly missed?
5. What happens if a defect is found after cutover?
6. Could you sponsor a paid, nonproduction design-partner rehearsal if the product passes the technical gates?

**Record evidence:** contact, role, type of project, current validation method, sign-off owner, urgency, objections, next action and explicit willingness to pay. No inferred purchase intent.

## Success criteria for first two weeks

- 15 relevant firms researched (not fabricated)
- 10 personalized messages sent with permission and tracked
- 3 discovery conversations targeted (goal, not forecast)
- 1 written pilot scope proposed only after readiness gates
- No customer data or credentials collected during prospecting

## Public demo claim

> “MigrationProof is an early-stage, evidence-first SQL migration reconciliation prototype. In a controlled test, it can compare selected schemas, row counts and numeric aggregates and surface discrepancies. It is not yet a production migration certification tool.”
