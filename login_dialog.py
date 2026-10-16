from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox,
)

from auth import authenticate


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

    def try_login(self):
        user = authenticate(self.username.text().strip(), self.password.text())
        if user is None:
            QMessageBox.warning(self, "Ошибка входа", "Неверный логин или пароль.")
            self.password.clear()
            return
        self.user = user
        self.accept()