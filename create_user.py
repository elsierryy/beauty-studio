import getpass

import psycopg

from auth import hash_password
from db import get_connection


def main():
    username = input("Логин: ").strip()
    role = input("Роль (admin или master): ").strip()
    if not username or role not in ("admin", "master"):
        print("Нужен логин и роль admin или master.")
        return

    master_id = None
    if role == "master":
        with get_connection() as conn:
            masters = conn.execute(
                "SELECT id, first_name FROM masters WHERE is_active ORDER BY id"
            ).fetchall()
        for m_id, name in masters:
            print(m_id, name)
        master_id = int(input("Номер мастера из списка: "))

    password = getpass.getpass("Пароль: ")
    if len(password) < 6:
        print("Пароль должен быть не короче 6 символов.")
        return
    if password != getpass.getpass("Повторите пароль: "):
        print("Пароли не совпадают.")
        return

    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, role, master_id) "
                "VALUES (%s, %s, %s, %s)",
                (username, hash_password(password), role, master_id),
            )
    except psycopg.errors.UniqueViolation:
        print("Такой логин уже есть.")
        return
    except psycopg.errors.ForeignKeyViolation:
        print("Мастера с таким номером нет.")
        return

    print("Пользователь создан.")


main()