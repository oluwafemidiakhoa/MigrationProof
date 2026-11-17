# Optional SQL Server SNAPSHOT transaction — lab-only

This experimental collector mode is **off by default**. On a separately approved disposable SQL Server test database, add `--snapshot-isolation` to the existing `migrationproof.sqlserver_cli` command.

It performs a read-only preflight of `sys.databases.snapshot_isolation_state` for the currently connected database. The mode refuses to run if the state is not **ON (1)**. It does **not** enable snapshot isolation or change database settings. Only an authorized DBA may separately approve that change on a disposable lab.

When enabled, the collector executes `SET TRANSACTION ISOLATION LEVEL SNAPSHOT` and `BEGIN TRANSACTION` before querying database identity, metadata and allowed-table rows. It attempts to roll back the transaction on every exit path, including errors. Any setup/query/rollback failure means the collection is incomplete.

The connection remains configured with `readonly=True`, `autocommit=True` and TLS validation. `readonly=True` is not a database-side permission guarantee: the operator must use a separately configured least-privilege login.

## Restrictions

- **Do not enable snapshot isolation on a production or corporate database for this project.**
- Snapshot isolation may consume row-version store space and change performance behavior; measure it in the lab.
- An opt-in transaction provides a candidate for consistent reads within **one** SQL Server database. Real transaction behavior, metadata visibility, schema changes during collection, query plans, RLS and version-store load still require independently reviewed SQL Server integration tests.
- Separate source/target transactions do **not** prove a shared point in time across databases or servers. The cross-database coherence assessment must remain **INCOMPLETE**.
- Do not issue any DML/DDL or `ALTER DATABASE` in the collector. Configuration changes remain manual and explicitly authorized.
- Do not claim a customer migration certificate or database equivalence solely from this option.
