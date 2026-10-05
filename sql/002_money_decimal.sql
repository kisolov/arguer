-- Для БД, где баланс и суммы хранились в DOUBLE.
-- На новой БД колонки сразу создаются как DECIMAL(14,2) (create_all).
-- Перед запуском остановите бота: ALTER перестраивает таблицы.

-- 1. Посмотреть, что изменится при округлении до сотых. Значения вроде
--    974.835 станут 974.84: так их и видел пользователь (формат .2f).
SELECT id, bal, ROUND(bal, 2) AS will_be FROM users WHERE bal <> ROUND(bal, 2);
SELECT id, amount, ROUND(amount, 2) AS will_be FROM transactions
WHERE amount <> ROUND(amount, 2);

-- 2. Сменить тип. MySQL округляет существующие значения до сотых.
ALTER TABLE users MODIFY bal DECIMAL(14, 2);
ALTER TABLE transactions MODIFY amount DECIMAL(14, 2);
