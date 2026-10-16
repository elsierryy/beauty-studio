import psycopg
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox,
    QPlainTextEdit,
)

from db import get_connection


class ClientDialog(QDialog):
    """Окно добавления клиента. Если передан client, то редактирования."""

    def __init__(self, client=None, parent=None):
        super().__init__(parent)
        self.client_id = client[0] if client else None
        self.setWindowTitle("Редактирование клиента" if client else "Новый клиент")
        self.resize(400, 300)

        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+79001234567")
        self.email = QLineEdit()
        self.notes = QPlainTextEdit()

        if client:
            _, first, last, phone, email, notes = client
            self.first_name.setText(first)
            self.last_name.setText(last or "")
            self.phone.setText(phone)
            self.email.setText(email or "")
            self.notes.setPlainText(notes or "")

        form = QFormLayout(self)
        form.addRow("Имя:", self.first_name)
        form.addRow("Фамилия:", self.last_name)
        form.addRow("Телефон:", self.phone)
        form.addRow("Email:", self.email)
        form.addRow("Заметки:", self.notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def save(self):
        first = self.first_name.text().strip()
        phone = self.phone.text().strip()

        if not first:
            QMessageBox.warning(self, "Ошибка", "Укажите имя клиента.")
            return
        if sum(ch.isdigit() for ch in phone) < 10:
            QMessageBox.warning(self, "Ошибка",
                                "Телефон должен содержать не меньше 10 цифр.")
            return

        values = (
            first,
            self.last_name.text().strip() or None,
            phone,
            self.email.text().strip() or None,
            self.notes.toPlainText().strip() or None,
        )

        try:
            with get_connection() as conn:
                if self.client_id is None:
                    conn.execute(
                        "INSERT INTO clients "
                        "(first_name, last_name, phone, email, notes) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        values,
                    )
                else:
                    conn.execute(
                        "UPDATE clients SET first_name = %s, last_name = %s, "
                        "phone = %s, email = %s, notes = %s WHERE id = %s",
                        values + (self.client_id,),
                    )
        except psycopg.errors.UniqueViolation:
            QMessageBox.warning(self, "Дубликат",
                                "Клиент с таким телефоном уже есть.")
            return

        self.accept()