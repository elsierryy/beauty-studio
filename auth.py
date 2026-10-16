import bcrypt

from db import get_connection


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def authenticate(username, password):
    """Возвращает данные пользователя или None, если логин или пароль неверны."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, role, master_id, client_id "
            "FROM users WHERE username = %s AND is_active",
            (username,),
        ).fetchone()

    if row is None or not check_password(password, row[2]):
        return None
    return {
        "id": row[0],
        "username": row[1],
        "role": row[3],
        "master_id": row[4],
        "client_id": row[5],
    }