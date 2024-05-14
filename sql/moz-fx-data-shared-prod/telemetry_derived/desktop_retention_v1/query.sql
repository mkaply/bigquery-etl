SELECT
  metric_date,
  first_seen_date,
  normalized_channel,
  country,
  app_version,
  locale,
  attribution_campaign,
  attribution_content,
  attribution_dlsource,
  attribution_medium,
  attribution_ua,
  normalized_os,
  normalized_os_version,
  COUNTIF(ping_sent_metric_date) AS ping_sent_metric_date,
  COUNTIF(ping_sent_week_4) AS ping_sent_week_4,
  COUNTIF(active_metric_date) AS active_metric_date,
  COUNTIF(retained_week_4) AS retained_week_4,
  COUNTIF(retained_week_4_new_profile) AS retained_week_4_new_profiles,
  COUNTIF(new_profile_metric_date) AS new_profiles_metric_date,
  COUNTIF(repeat_profile) AS repeat_profiles,
FROM
  `moz-fx-data-shared-prod.telemetry_derived.desktop_retention_clients_v1`
WHERE
  metric_date = DATE_SUB(@submission_date, INTERVAL 27 DAY)
  AND submission_date = @submission_date
GROUP BY
  metric_date,
  first_seen_date,
  normalized_channel,
  country,
  app_version,
  locale,
  attribution_campaign,
  attribution_content,
  attribution_dlsource,
  attribution_medium,
  attribution_ua,
  normalized_os,
  normalized_os_version
