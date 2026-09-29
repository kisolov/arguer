-- Для БД, созданной до появления уникального индекса на users.telegram_id.
-- На новой БД индекс создаётся сам при старте бота (create_all).

-- 1. Найти дубли. Если запрос пуст, сразу переходите к шагу 3.
SELECT telegram_id, COUNT(*) AS copies, MIN(id) AS keep_id
FROM users
GROUP BY telegram_id
HAVING COUNT(*) > 1;

-- 2. Слить дубли вручную для каждого telegram_id: переназначить транзакции
--    на оставляемую запись (keep_id), сложить балансы и удалить лишние строки.
--    Пример для одной пары (keep = 1, дубль = 7):
--      UPDATE transactions SET `user` = 1 WHERE `user` = 7;
--      UPDATE users SET bal = bal + (SELECT bal FROM (SELECT bal FROM users WHERE id = 7) AS t) WHERE id = 1;
--      DELETE FROM users WHERE id = 7;
--    Автоматически не делаем: решение, чей баланс считать верным, за вами.

-- 3. Создать индекс. Имя совпадает с тем, что создаёт модель.
CREATE UNIQUE INDEX ix_users_telegram_id ON users (telegram_id);
