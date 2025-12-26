-- Инициализация базы данных для Shop Manager Bot

-- Настройка кодировки
SET client_encoding = 'UTF8';

-- Создание индексов для оптимизации (будут созданы автоматически при запуске приложения)
-- Но можно добавить дополнительные инициализации здесь

-- Пример: создание дополнительных пользователей или настроек
-- INSERT INTO some_table (column) VALUES ('value') ON CONFLICT DO NOTHING;

-- Логирование инициализации
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed for Shop Manager Bot';
END
$$;
