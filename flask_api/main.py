from flask import Flask, jsonify
import psycopg
from psycopg.rows import dict_row
# Создаём Flask-приложение.

app = Flask(__name__)
app.json.sort_keys = False # отключаем сортировку ключей JSON

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "dbname": "db_notes",
    "user": "postgres",
    "password": "1234"
}

def get_db():
    return psycopg.connect(
        **DB_CONFIG,
        row_factory=dict_row,
        connect_timeout=3
    )

# Маршрут для проверки работы API.
@app.get("/")
def root():
    return {"message": "Notes API is running"}

@app.get("/notes")
def get_notes():
    # Открываем соединение с базой данных.
    with get_db() as conn:
        # Выполняем SQL-запрос и получаем все найденные строки.
        notes = conn.execute(
            """
            SELECT
                n.id,
                CONCAT(n.title, ' - ', u.login) AS title_user,
                n.content,
                TO_CHAR(n.created_at, 'DD.MM.YYYY') AS formatted_date
            FROM notes AS n
            JOIN users AS u ON u.id = n.id_user
            ORDER BY n.id
            """
        ).fetchall()

    # Преобразуем результат в JSON и отправляем клиенту.
    return jsonify(notes)


# Запускаем сервер, если файл main.py запущен напрямую.
if __name__ == "__main__":
    app.run(debug=True)