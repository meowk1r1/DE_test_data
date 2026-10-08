from werkzeug.security import generate_password_hash

password = input("Введите пароль: ")
print(generate_password_hash(password))