-- dialect: postgres
-- Sample PostgreSQL queries with anti-patterns

-- Rule: select-star
SELECT * FROM users WHERE active = true;

-- Rule: missing-where-delete
DELETE FROM sessions;

-- Rule: missing-where-update
UPDATE users SET status = 'inactive';

-- Rule: leading-wildcard-like
SELECT id, name FROM products WHERE name LIKE '%widget%';

-- Rule: implicit-column-order (INSERT without column list)
INSERT INTO orders VALUES (1, 'pending', NOW());

-- Rule: hardcoded-credentials
SELECT * FROM configs WHERE password = 'admin123';

-- Rule: cartesian-join (CROSS JOIN)
SELECT a.id, b.name FROM users a CROSS JOIN orders b;

-- Rule: order-by-ordinal
SELECT name, email FROM users ORDER BY 2;

-- Rule: null-comparison
SELECT * FROM users WHERE deleted_at = NULL;
