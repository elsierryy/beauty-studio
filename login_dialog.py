from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox, QPushButton,
)

from auth import authenticate
from register_dialog import RegisterDialog


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Вход")
        self.user = None

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout(self)
        form.addRow("Логин:", self.username)
        form.addRow("Пароль:", self.password)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.try_login)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        register_button = QPushButton("Зарегистрироваться")
        register_button.clicked.connect(self.open_register)
        form.addRow(register_button)

    def open_register(self):
        dialog = RegisterDialog(self)
        if dialog.exec():
            self.username.setText(dialog.username_value)
            self.password.clear()
            self.password.setFocus()

    def try_login(self):
        user = authenticate(self.username.text().strip(), self.password.text())
        if user is None:
            QMessageBox.warning(self, "Ошибка входа", "Неверный логин или пароль.")
            self.password.clear()
            return
        self.user = user
        self.accept()