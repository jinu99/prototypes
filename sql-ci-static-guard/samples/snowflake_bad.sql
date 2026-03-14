-- dialect: snowflake
-- Sample Snowflake queries with anti-patterns

-- Rule: select-star
SELECT * FROM raw.events;

-- Rule: missing-where-update
UPDATE staging.dim_users SET is_active = FALSE;

-- Rule: leading-wildcard-like
SELECT event_id FROM analytics.events WHERE event_name LIKE '_click%';

-- Rule: implicit-column-order
INSERT INTO warehouse.fact_orders VALUES ('2024-01-01', 100, 49.99);

-- Rule: cartesian-join (comma-join without WHERE)
SELECT a.user_id, b.order_id FROM users a, orders b;

-- Rule: hardcoded-credentials
SELECT * FROM credentials WHERE secret = 'super-secret-token';

-- Rule: null-comparison
SELECT * FROM sessions WHERE ended_at = NULL;
