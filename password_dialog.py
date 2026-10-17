from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox,
)

from auth import check_password, hash_password
from db import get_connection


class PasswordDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Смена пароля")

        self.old = QLineEdit()
        self.new = QLineEdit()
        self.new2 = QLineEdit()
        for field in (self.old, self.new, self.new2):
            field.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout(self)
        form.addRow("Текущий пароль:", self.old)
        form.addRow("Новый пароль:", self.new)
        form.addRow("Повторите новый:", self.new2)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def warn(self, text):
        QMessageBox.warning(self, "Ошибка", text)

    def save(self):
        if len(self.new.text()) < 6:
            return self.warn("Новый пароль должен быть не короче 6 символов.")
        if self.new.text() != self.new2.text():
            return self.warn("Новые пароли не совпадают.")

        with get_connection() as conn:
            row = conn.execute(
                "SELECT password_hash FROM users WHERE id = %s", (self.user_id,)
            ).fetchone()
        if row is None or not check_password(self.old.text(), row[0]):
            return self.warn("Текущий пароль неверный.")

        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (hash_password(self.new.text()), self.user_id),
            )
        QMessageBox.information(self, "Готово", "Пароль изменён.")
        self.accept()