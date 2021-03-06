-- view for org_mozilla_firefox__view_clients_daily_scalar_aggregates_v1;
-- View to union daily scalar aggregates with date partitioning
CREATE OR REPLACE VIEW
  `moz-fx-data-shared-prod.glam_etl.org_mozilla_firefox__view_clients_daily_scalar_aggregates_v1`
AS
SELECT
  * EXCEPT (submission_date),
  DATE(_PARTITIONTIME) AS submission_date
FROM
  `moz-fx-data-shared-prod.glam_etl.org_mozilla_firefox__clients_daily_scalar_aggregates*`
