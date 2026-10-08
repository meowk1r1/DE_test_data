from flask import Flask, render_template, request, redirect, flash, session
import psycopg
from psycopg.rows import dict_row
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

DB = {
    "host": "127.0.0.1",
    "port": 5433,
    "dbname": "de_app",
    "user": "postgres",
    "password": "1234"
}

def get_db():
    return psycopg.connect(**DB, row_factory=dict_row, connect_timeout=3)

app = Flask(__name__)  # создаём Flask-приложение
app.secret_key = "de-yurov-AKLDO912319g9191992392900cjJIJi3jij32oi1fi0013cJJED"



@app.errorhandler(psycopg.Error)
def database_error(error):
    return f"Ошибка работы с базой данных. Проверьте настройки PostgreSQL. {error}", 500

@app.get("/check")  # маршрут GET /check,  функция ниже выполняется при переходе на /check
def check(): 
    return "Flask работает"  # ответ браузеру

@app.get("/")
def login_page():
    return render_template("login.html")

@app.post("/login")
def login():
    # Получаем логин, пароль из отправленной формы. Ключи "login" и "password" совпадают с атрибутами name в login.html
    login_value = request.form["login"]
    password = request.form["password"]
    captcha = request.form["captcha"]
    # Открываем соединение с PostgreSQL.
    with get_db() as conn:
        # Ищем пользователя с таким логином.
        user = conn.execute("SELECT * FROM users WHERE login = %s",(login_value,)).fetchone()

        # Если такого логина в БД нет -- возвращаем пользователя на страницу входа.
        if not user:
            flash("Вы ввели неверный логин или пароль. Пожалуйста, проверьте введённые данные.","error")
            return redirect("/")

        # Если пользователь уже заблокирован -- вход запрещён.
        if user["blocked"]:
            flash("Вы заблокированы. Обратитесь к администратору.", "error")
            return redirect("/")

        # Сравниваем введённый пароль с хешем из базы данных.
        password_ok = check_password_hash(user["password"], password)

        # Если пароль неверный -- увеличиваем число неудачных попыток.
        if not password_ok or captcha != "ok":
            attempts = user["attempts"] + 1

            # После третьей неудачной попытки blocked станет True.
            blocked = attempts >= 3

            # Сохраняем новое число попыток и состояние блокировки.
            conn.execute("UPDATE users SET attempts=%s, blocked=%s WHERE id=%s", (attempts, blocked, user["id"]))

            if blocked:
                flash("Вы заблокированы. Обратитесь к администратору.", "error")
            else:
                flash("Неверный пароль или пазл собран неправильно.", "error")

            return redirect("/")

        # Пароль верный -- сбрасываем счётчик неудачных попыток.
        conn.execute("UPDATE users SET attempts=0 WHERE id=%s", (user["id"],))

    # Запоминаем вошедшего пользователя в сессии Flask.
    session["role"] = user["role"]
    session["login"] = user["login"]
    
    # Переходим на страницу успешного входа.
    if user["role"] == "Администратор":
        flash("Вы успешно авторизовались.", "success")
        return redirect("/admin")

    return redirect("/success")

@app.get("/success")
def success():
    if "login" not in session:
        return redirect("/")

    return f"""
    <h2>Вы успешно авторизовались.</h2>
    <p>Пользователь: {session['login']}</p>
    <p><a href="/logout">Выйти</a></p>
    """


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.get("/admin")
def admin_page():
    if session.get("role") != "Администратор":
        return redirect("/")

    with get_db() as conn:
        users = conn.execute(
            "SELECT * FROM users ORDER BY id"
        ).fetchall()

    return render_template("admin.html", users=users)

@app.post("/admin/add")
def add_user():
    # Разрешаем добавление пользователей только администратору.
    if session.get("role") != "Администратор":
        return redirect("/")

    # Получаем данные из формы.Пароль сразу превращаем в хеш -- в открытом виде его не сохраняем.
    login_value = request.form["login"]
    password = generate_password_hash(request.form["password"])
    role = request.form["role"]

    # Открываем соединение с PostgreSQL.
    with get_db() as conn:
        # Проверяем, нет ли уже пользователя с таким логином.
        exists = conn.execute("SELECT id FROM users WHERE login=%s", (login_value,)).fetchone()

        # Если логин уже существует -- нового пользователя не добавляем.
        if exists:
            flash("Пользователь с таким логином уже существует.", "error")
            return redirect("/admin")

        # Добавляем нового пользователя в таблицу users.
        conn.execute("INSERT INTO users (login, password, role) VALUES (%s, %s, %s)",(login_value, password, role))

    # Показываем сообщение об успешном добавлении и возвращаемся на страницу администратора.
    flash("Пользователь добавлен.", "success")
    return redirect("/admin")

@app.get("/edit/<int:user_id>")
def edit_page(user_id):
    # Разрешаем открывать страницу редактирования только администратору.
    if session.get("role") != "Администратор":
        return redirect("/")

    # Ищем пользователя по id, который пришёл из адреса страницы.
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=%s", (user_id,)).fetchone()

    # Если пользователя с таким id нет -- возвращаемся к списку пользователей.
    if not user:
        return redirect("/admin")

    # Открываем страницу edit.html и передаём в неё найденного пользователя.
    return render_template("edit.html", user=user)


@app.post("/edit/<int:user_id>")
def edit_save(user_id):
    # Разрешаем сохранять изменения только администратору.
    if session.get("role") != "Администратор":
        return redirect("/")

    # Получаем новые данные пользователя из HTML-формы.
    login_value = request.form["login"]

    # Хешируем введённый пароль перед сохранением в базу.
    password = generate_password_hash(request.form["password"])

    role = request.form["role"]

    # Checkbox отправляет поле blocked только тогда, когда пользователь поставил галочку. Поэтому выражение сразу даёт True или False.
    blocked = "blocked" in request.form

    # Открываем соединение с PostgreSQL.
    with get_db() as conn:

        # Проверяем, не занят ли новый логин другим пользователем.Текущего пользователя исключаем из проверки по его id.
        duplicate = conn.execute("SELECT id FROM users WHERE login=%s AND id!=%s", (login_value, user_id)).fetchone()

        # Если такой логин уже используется -- изменения не сохраняем.
        if duplicate:
            flash("Пользователь с таким логином уже существует.", "error")
            return redirect(f"/edit/{user_id}")

        # Обновляем данные выбранного пользователя.После сохранения счётчик ошибочных попыток сбрасываем в 0.
        conn.execute("UPDATE users SET login=%s, password=%s, role=%s, blocked=%s, attempts=0 WHERE id=%s",
            (login_value, password, role, blocked, user_id)
        )

    # Сообщаем об успешном сохранении и возвращаемся к списку пользователей.
    flash("Данные пользователя сохранены.", "success")
    return redirect("/admin")

if __name__ == "__main__":
    app.run(debug=True) 
