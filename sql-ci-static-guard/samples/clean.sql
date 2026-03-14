-- dialect: postgres
-- A clean SQL file with no anti-patterns

SELECT id, name, email
FROM users
WHERE active = true
  AND created_at > '2024-01-01'
ORDER BY name;

DELETE FROM sessions WHERE expired_at < NOW();

UPDATE users SET last_login = NOW() WHERE id = 42;

INSERT INTO audit_log (user_id, action, created_at)
VALUES (42, 'login', NOW());

SELECT u.id, u.name, o.total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE o.status = 'completed'
ORDER BY o.total DESC;

SELECT id FROM users WHERE deleted_at IS NULL;
