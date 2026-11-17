# MigrationProof — end-to-end product blueprint (2026-11-17)

## Intended product claim

Independent, evidence-first **SQL Server migration reconciliation**. Customers receive a decision-support report describing what was observed, compared, missing and not tested. Never call this a certification of complete equivalence, full security, or business continuity absent separately verified requirements and independent review.

## Design principles

- **NO-GO on unsupported claims**: report PASS, FAIL, INCOMPLETE, NOT_TESTED and NOT_APPLICABLE per check and an overall scoped assessment. Unknowns cannot become PASS.
- Collector performs read-only SQL queries using an explicitly authorized, scoped account. Neither scanner nor web tier executes mutation SQL against customer systems.
- Run collection near each customer environment; locally generate sanitized, minimized output; cloud upload is opt-in and subject to contractual authorization.
- Separate database access plane from control plane, report view, and billing. No arbitrary SQL from a model or browser.
- Comparison correctness outranks visual polish; freeze evidence, parser versions, and check semantics before presenting a result.
- Gate every non-production release on security and failure-path tests; never promote to production without explicit, environment-specific permission.

## Proposed architecture

```text
Customer operator (CLI/desktop agent)
  -> signed collection manifest + bounded, audited read-only collectors
  -> local encrypted, redacted evidence bundle
  -> deterministic reconciliation engine
  -> normalized finding ledger + versioned coverage contract
  -> signed report/artifact manifest
  -> local HTML/PDF report
           optional consented upload
               -> secured API / tenant RBAC / encrypted object storage
               -> pilot dashboard / export / invoicing
```

## Milestone A: verified offline engine

Deliverables:
1. Typed schema and aggregate comparisons; canonical numeric semantics (decimal, null, collation/time zone).
2. Deterministic keyed row fingerprints where permitted; salt/pseudonymize sensitive identifiers; test collisions and canonicalization.
3. Equal-count/equal-sum-but-different-rows fixtures, missing objects, different collations and nullability, overflow, timestamp skew.
4. Versioned evidence schema, collected_at, engine revision, completeness and scope/status on every finding.
5. Reproducible unit/property/metamorphic and fuzz tests plus CLI contract tests.

Exit gate: tests demonstrate both positive and negative cases. No database connectivity claims.

## Milestone B: authorized SQL Server connector

Deliverables:
1. Dedicated bounded, read-only account; exact server/database identity, TLS chain validation, object allowlists and permissions.
2. Explicit query workload limits: timeouts, per-table caps, cancel controls, dry-run cost/size estimation, controlled concurrency.
3. Metadata visibility/completeness check independent of permissions granted to collector; deny/flag insufficient privileges.
4. Transactionally coherent source or target snapshot strategy, with measured source-target capture skew and logging.
5. Real disposable SQL Server 2019/2022/2025 lab matrix as supported, ODBC 18, negative auth/certificate/RLS/timeouts tests.
6. Never issue customer production connections without written approval, scope, and an operator-operated collector.

Exit gate: bounded lab integration tests with receipts; live production readiness remains gated.

## Milestone C: decision-grade proof bundle

Deliverables:
1. Manifest with source/target logical identities, collection time, scope, engine version, check configuration, digests and caveats.
2. Artifact digest and signature with verifiable signer identity; reproducible reports with evidence-item IDs.
3. Report summary, differences, confidence limits, incomplete/untested checks, remediation owner and recheck evidence.
4. Evidence export as JSON and accessible HTML/PDF; signed bundles and independently runnable verifier.
5. Default privacy minimization, encryption, retention policies, no raw row values in central telemetry.

Exit gate: independent bundle re-verification from an air-gapped machine and tamper detection.

## Milestone D: commercial pilot (not enterprise SaaS yet)

Deliverables:
1. Synthetic demo of a same-row-count migration defect and missing-table case.
2. Operator runbook, data processing agreement and explicit per-customer scope.
3. Productized fixed-fee pilot workflow: discovery, approved collection, review, documented findings, remediation recheck.
4. Pilot acceptance questionnaire, outcome instrumentation and buyer feedback log.
5. No sales claim of certification, zero-risk migration, or independent validation without substantiation.

Exit gate: approved design-partner engagement and signed acceptance criteria.

## Milestone E: multi-tenant SaaS (only after pilots show need)

Deliverables:
1. Authentication, organization/tenant RBAC, billing, rate/concurrency quotas, audit trail and signed report access.
2. Server-side tenant isolation for storage, queue jobs, caches, search, exports, logs and admin access; adversarial cross-tenant tests.
3. SLOs, traces/alerts, incident response, durable jobs, backups plus verified restoration, region-aware residency policy.
4. Versioned collector distribution with provenance and signed updates, release/canary/rollback process.
5. Human-reviewed customer consent for any connector installation and data transfer.

Exit gate: external security review, restore drills, legal/privacy approval, production operational readiness.

## Critical negative tests

- Hidden table/column => INCOMPLETE; cannot produce a clean PASS.
- Different data with matching count and SUM => reconciliation must detect when row-level scope is enabled.
- Mismatched expected DB / malicious identifier / unauthorized scope => refused before query.
- Untrusted TLS / credential mismatch / wrong server certificate => refused.
- Timeout / RLS / schema change during scan / snapshot skew => flagged, not silently ignored.
- Data beyond budget => bounded abort, not unbounded fallback.
- Tampered manifest / changed evidence file / wrong signature => verification fails.
- Cross-tenant report lookup / download / job ID substitution => denied.
- Missing telemetry or backup restore evidence => production readiness INCOMPLETE.
- Duplicate webhook / billing event => idempotent and reconciled if commerce enabled.

## Operational launch gate

A production release requires: exact commit/artifact identity, verified CI and integration, security negative tests, authorized data-collection boundaries, privacy review, recovery evidence, observable error-budget targets, cost controls, immutable report and rollback plan. Otherwise NO-GO/INCOMPLETE.

## Definition of honest completion

A feature is implemented only with code and tests. A risk is fixed only with targeted verification. A system is production ready only after applicable operational and customer-specific gates have independent evidence.
