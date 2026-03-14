-- dialect: mysql
-- Sample MySQL queries with anti-patterns

-- Rule: select-star
SELECT * FROM inventory;

-- Rule: missing-where-delete
DELETE FROM temp_logs;

-- Rule: leading-wildcard-like
SELECT product_id FROM catalog WHERE sku LIKE '%ABC';

-- Rule: hardcoded-credentials
UPDATE accounts SET api_key = 'sk-12345-secret' WHERE id = 1;

-- Rule: null-comparison
SELECT * FROM users WHERE email != NULL;

-- Rule: order-by-ordinal
SELECT first_name, last_name, email FROM customers ORDER BY 1, 3;
