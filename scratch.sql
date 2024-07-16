DELETE FROM `maddictdata.Metadata.Campaign_Tracker`
WHERE code_name = 9999;

'''Process for meta data'''
##
SELECT
  *
FROM
  `maddictdata.Metadata.Campaign_Tracker`
WHERE
  status = 'Completion Period';

-- Updated
UPDATE `maddictdata.Metadata.test`
SET status = CASE
    WHEN CURRENT_DATE() < start_date THEN 'Validation'
    WHEN CURRENT_DATE() BETWEEN start_date AND end_date THEN 'Active'
    WHEN CURRENT_DATE() > end_date THEN 'Completion Period'
    ELSE status
END
WHERE status IN ('Pre-Validation', 'Validation', 'Active');


SELECT
  id,
  code_name,
  campaign_name,
  start_date,
  end_date,
  country,
  type,
  backend_report,
  time_interval,
  last_update,
  CASE
    WHEN CURRENT_DATE() < start_date THEN "Validation"
    WHEN CURRENT_DATE() BETWEEN start_date
  AND end_date THEN "Active"
    ELSE status
END
  AS updated_status
FROM
  `maddictdata.Metadata.Campaign_Tracker`;

--
SELECT
  id,
  code_name,
  campaign_name,
  start_date,
  end_date,
  country,
  type,
  backend_report,
  time_interval,
  last_update,
  status
FROM
  `maddictdata.Metadata.Campaign_Tracker`
WHERE
  status = 'Active'
  AND DATE_SUB(CURRENT_DATE(), INTERVAL time_interval DAY) > DATE(last_update);