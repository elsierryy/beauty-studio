import psycopg
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox,
)

from auth import hash_password
from db import get_connection


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Регистрация")
        self.resize(350, 250)
        self.username_value = None

        self.username = QLineEdit()
        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+79001234567")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password2 = QLineEdit()
        self.password2.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout(self)
        form.addRow("Логин:", self.username)
        form.addRow("Имя:", self.first_name)
        form.addRow("Фамилия:", self.last_name)
        form.addRow("Телефон:", self.phone)
        form.addRow("Пароль:", self.password)
        form.addRow("Повторите пароль:", self.password2)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def warn(self, text):
        QMessageBox.warning(self, "Ошибка", text)

    def save(self):
        username = self.username.text().strip()
        first = self.first_name.text().strip()
        last = self.last_name.text().strip() or None
        phone = self.phone.text().strip()
        password = self.password.text()

        if len(username) < 3:
            return self.warn("Логин должен быть не короче 3 символов.")
        if not first:
            return self.warn("Укажите имя.")
        if sum(ch.isdigit() for ch in phone) < 10:
            return self.warn("Телефон должен содержать не меньше 10 цифр.")
        if len(password) < 6:
            return self.warn("Пароль должен быть не короче 6 символов.")
        if password != self.password2.text():
            return self.warn("Пароли не совпадают.")

        try:
            with get_connection() as conn:
                client_id = conn.execute(
                    "INSERT INTO clients (first_name, last_name, phone) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    (first, last, phone),
                ).fetchone()[0]
                conn.execute(
                    "INSERT INTO users (username, password_hash, role, client_id) "
                    "VALUES (%s, %s, 'client', %s)",
                    (username, hash_password(password), client_id),
                )
        except psycopg.errors.UniqueViolation as e:
            if e.diag.constraint_name == "users_username_key":
                return self.warn("Этот логин уже занят.")
            return self.warn(
                "Клиент с таким телефоном уже есть. "
                "Обратитесь к администратору салона."
            )

        self.username_value = username
        QMessageBox.information(self, "Готово",
                                "Регистрация прошла успешно. Теперь войдите.")
        self.accept()