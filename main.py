import sys

from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QMainWindow, QPushButton, QTabWidget,
    QWidget,
)

from appointments_tab import AppointmentsTab
from catalog_tab import CatalogTab
from clients_tab import ClientsTab
from login_dialog import LoginDialog
from password_dialog import PasswordDialog
from reports_tab import ReportsTab


class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.logout_requested = False
        self.setWindowTitle(f"Студия красоты, вы вошли как {user['username']}")
        self.resize(1150, 550)

        self.tabs = QTabWidget()
        self.tabs.addTab(AppointmentsTab(user), "Записи")
        if user["role"] in ("admin", "master"):
            self.tabs.addTab(ClientsTab(), "Клиенты")
        if user["role"] == "admin":
            self.tabs.addTab(CatalogTab(), "Справочники")
            self.tabs.addTab(ReportsTab(), "Отчёты")
        self.tabs.currentChanged.connect(self.refresh_tab)

        password_button = QPushButton("Сменить пароль")
        password_button.clicked.connect(self.change_password)
        logout_button = QPushButton("Выйти")
        logout_button.clicked.connect(self.logout)

        corner = QWidget()
        corner_layout = QHBoxLayout(corner)
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.addWidget(password_button)
        corner_layout.addWidget(logout_button)
        self.tabs.setCornerWidget(corner)

        self.setCentralWidget(self.tabs)

    def refresh_tab(self, index):
        self.tabs.widget(index).refresh()

    def change_password(self):
        PasswordDialog(self.user["id"], self).exec()

    def logout(self):
        self.logout_requested = True
        self.close()


def main():
    app = QApplication(sys.argv)
    while True:
        login = LoginDialog()
        if login.exec() != QDialog.DialogCode.Accepted:
            break
        window = MainWindow(login.user)
        window.show()
        app.exec()
        if not window.logout_requested:
            break


main()