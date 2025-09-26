import psycopg2
from psycopg2 import sql

DB_CONFIG = {
}


def create_database_and_user():
    # Подключаемся к базе данных postgres по умолчанию
    conn = psycopg2.connect(
        **DB_CONFIG
    )
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        # Создаем базу данных kanban
        cursor.execute("CREATE DATABASE kanban;")
        print("База данных 'kanban' создана успешно")
    except psycopg2.Error as e:
        print(f"База данных уже существует: {e}")

    try:
        # Создаем пользователя (можно пропустить, если используем postgres)
        cursor.execute("CREATE USER kanban_user WITH PASSWORD 'kanban_password';")
        print("Пользователь 'kanban_user' создан успешно")
    except psycopg2.Error as e:
        print(f"Пользователь уже существует: {e}")

    try:
        # Даем права пользователю
        cursor.execute("GRANT ALL PRIVILEGES ON DATABASE kanban TO kanban_user;")
        print("Права предоставлены успешно")
    except psycopg2.Error as e:
        print(f"Ошибка предоставления прав: {e}")

    cursor.close()
    conn.close()


def create_tables():
    # Подключаемся к нашей новой базе данных
    from db_client import PostgresDB

    db = PostgresDB(
        **DB_CONFIG
    )

    # SQL для создания таблицы задач
    create_tasks_table = """
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        status VARCHAR(50) NOT NULL DEFAULT 'backlog',
        assignee VARCHAR(100),
        priority VARCHAR(20) NOT NULL DEFAULT 'medium',
        due_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    # SQL для создания таблицы исполнителей
    create_assignees_table = """
    CREATE TABLE IF NOT EXISTS assignees (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        email VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    try:
        db.create_table(create_tasks_table)
        print("Таблица 'tasks' создана успешно")

        db.create_table(create_assignees_table)
        print("Таблица 'assignees' создана успешно")

        # Добавляем тестовых исполнителей
        initial_assignees = [
            "Иван Иванов",
            "Петр Петров",
            "Мария Сидорова",
            "Алексей Козлов",
            "Анна Смирнова",
            "Дмитрий Волков"
        ]

        for assignee in initial_assignees:
            db.upsert("assignees", {"name": assignee}, "name")
        print("Тестовые исполнители добавлены")

    except Exception as e:
        print(f"Ошибка создания таблиц: {e}")


if __name__ == "__main__":
    create_database_and_user()

    create_tables()
