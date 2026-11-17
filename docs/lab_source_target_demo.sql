/* MigrationProof demo only. Execute in SSMS on an explicitly approved TEST instance.
   Creates two NEW disposable databases; aborts if either exists.
   No DROP/ALTER of existing databases. Review server capacity/change approval first.
*/
USE master;
GO
IF DB_ID(N'MigrationProofSourceLab') IS NOT NULL OR DB_ID(N'MigrationProofTargetLab') IS NOT NULL
    THROW 51000, 'A demo database already exists; stop and investigate.', 1;
GO
CREATE DATABASE MigrationProofSourceLab;
GO
CREATE DATABASE MigrationProofTargetLab;
GO
USE MigrationProofSourceLab;
GO
CREATE TABLE dbo.Orders (OrderID int NOT NULL PRIMARY KEY, Amount decimal(12,2) NOT NULL);
INSERT dbo.Orders(OrderID,Amount) VALUES (1,50.00),(2,75.00),(3,25.00);
GO
USE MigrationProofTargetLab;
GO
CREATE TABLE dbo.Orders (OrderID int NOT NULL PRIMARY KEY, Amount decimal(12,2) NOT NULL);
INSERT dbo.Orders(OrderID,Amount) VALUES (1,50.00),(2,75.00),(3,25.00);
GO
/* Inject one intentional defect: same row count, different value. */
UPDATE dbo.Orders SET Amount=999.00 WHERE OrderID=3;
GO
SELECT DB_NAME() AS database_name, COUNT_BIG(*) AS row_count, SUM(Amount) AS total_amount FROM dbo.Orders;
GO
