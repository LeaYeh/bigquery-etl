-- Query generated by: templates/smoot_usage_raw.sql.py --source nondesktop_clients_last_seen_v1

WITH
  base AS (
    SELECT
      *,
      normalized_channel AS channel
    FROM
      nondesktop_clients_last_seen_v1
    WHERE
      -- We apply this filter here rather than in the live view because this field
      -- is not normalized and there are many single pings that come in with unique
      -- nonsensical app_name values. App names are documented in
      -- https://docs.telemetry.mozilla.org/concepts/choosing_a_dataset_mobile.html#products-overview
      (STARTS_WITH(app_name, 'FirefoxReality') OR app_name IN (
        'Fenix',
        'Fennec', -- Firefox for Android and Firefox for iOS
        'Focus',
        'FirefoxConnect', -- Amazon Echo
        'FirefoxForFireTV',
        'Zerda')) -- Firefox Lite, previously called Rocket
      -- There are also many strange nonsensical entries for os, so we filter here.
      AND os IN ('Android', 'iOS'))
  --
SELECT
  submission_date,
  COUNTIF(days_since_created_profile = 6) AS new_profiles,
  [ --
  STRUCT('Any Firefox Non-desktop Activity' AS usage,
    STRUCT(
      COUNTIF(days_since_seen < 1) AS dau,
      COUNTIF(days_since_seen < 7) AS wau,
      COUNTIF(days_since_seen < 28) AS mau,
      SUM(udf_bitcount_lowest_7(days_seen_bits)) AS active_days_in_week
    ) AS metrics_daily,
    STRUCT(
      COUNTIF(days_since_created_profile = 6 AND udf_active_n_weeks_ago(days_seen_bits, 0)) AS active_in_week_0,
      SUM(IF(days_since_created_profile = 6, udf_bitcount_lowest_7(days_seen_bits), 0)) AS active_days_in_week_0
    ) AS metrics_1_week_post_new_profile,
    STRUCT(
      COUNTIF(days_since_created_profile = 13 AND udf_active_n_weeks_ago(days_seen_bits, 0)) AS active_in_week_1,
      COUNTIF(days_since_created_profile = 13 AND udf_active_n_weeks_ago(days_seen_bits, 1) AND udf_active_n_weeks_ago(days_seen_bits, 0)) AS active_in_weeks_0_and_1
    ) AS metrics_2_week_post_new_profile),
  STRUCT('New Firefox Non-desktop Profile Created' AS usage,
    STRUCT(
      COUNTIF(days_since_created_profile < 1) AS dau,
      NULL AS wau,
      NULL AS mau,
      NULL AS active_days_in_week
    ) AS metrics_daily,
    STRUCT(
      NULL AS active_in_week_0,
      NULL AS active_days_in_week_0
    ) AS metrics_1_week_post_new_profile,
    STRUCT(
      NULL AS active_in_week_1,
      NULL AS active_in_weeks_0_and_1
    ) AS metrics_2_week_post_new_profile)
  ] AS metrics,
  -- We hash client_ids into 20 buckets to aid in computing
  -- confidence intervals for mau/wau/dau sums; the particular hash
  -- function and number of buckets is subject to change in the future.
  MOD(ABS(FARM_FINGERPRINT(client_id)), 20) AS id_bucket,
  app_name,
  app_version,
  country,
  locale,
  os,
  os_version,
  channel
FROM
  base
WHERE
  client_id IS NOT NULL
  -- Reprocess all dates by running this query with --parameter=submission_date:DATE:NULL
  AND (@submission_date IS NULL OR @submission_date = submission_date)
GROUP BY
  submission_date,
  id_bucket,
  app_name,
  app_version,
  country,
  locale,
  os,
  os_version,
  channel