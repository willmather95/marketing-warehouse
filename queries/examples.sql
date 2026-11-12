-- Questions agents ask the warehouse instead of calling the Search Console API.
-- duckdb warehouse/brain.duckdb < queries/examples.sql

-- 1. Is every site current?
SELECT brand, min_date, max_date, row_count FROM gsc_load_meta ORDER BY brand;

-- 2. Top queries for one site, last 28 days with data
WITH w AS (SELECT MAX(date) AS d FROM gsc_page_query WHERE brand = 'tool')
SELECT query, SUM(clicks) AS clicks, SUM(impressions) AS impressions,
       ROUND(SUM(position * impressions) / SUM(impressions), 1) AS avg_position
FROM gsc_page_query, w
WHERE brand = 'tool' AND date > w.d - INTERVAL 28 DAY
GROUP BY query ORDER BY impressions DESC LIMIT 20;

-- 3. Site-level average position, this 28 days vs the 28 before (the SEO scoreboard)
WITH w AS (SELECT MAX(date) AS d FROM gsc_page_query WHERE brand = 'tool')
SELECT CASE WHEN date > w.d - INTERVAL 28 DAY THEN 'this_28d' ELSE 'prior_28d' END AS window,
       ROUND(SUM(position * impressions) / SUM(impressions), 2) AS avg_position,
       SUM(clicks) AS clicks
FROM gsc_page_query, w
WHERE brand = 'tool' AND date > w.d - INTERVAL 56 DAY
GROUP BY 1 ORDER BY 1 DESC;

-- 4. Pages gaining impressions but not clicks (snippet or intent problem)
WITH w AS (SELECT MAX(date) AS d FROM gsc_page_query WHERE brand = 'tool'),
p AS (
  SELECT page,
         SUM(impressions) FILTER (WHERE date > w.d - INTERVAL 28 DAY) AS imp_now,
         SUM(impressions) FILTER (WHERE date <= w.d - INTERVAL 28 DAY) AS imp_before,
         SUM(clicks) FILTER (WHERE date > w.d - INTERVAL 28 DAY) AS clicks_now,
         SUM(clicks) FILTER (WHERE date <= w.d - INTERVAL 28 DAY) AS clicks_before
  FROM gsc_page_query, w WHERE brand = 'tool' AND date > w.d - INTERVAL 56 DAY GROUP BY page)
SELECT * FROM p WHERE imp_now > 1.2 * imp_before AND clicks_now <= clicks_before ORDER BY imp_now DESC;
