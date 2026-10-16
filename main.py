import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QDialog, QHBoxLayout, QHeaderView,
    QMainWindow, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from appointment_dialog import AppointmentDialog
from clients_tab import ClientsTab
from db import get_connection
from login_dialog import LoginDialog
from payment_dialog import PaymentDialog
from reports_tab import ReportsTab

QUERY = """
SELECT a.id,
       c.first_name || ' ' || COALESCE(c.last_name, ''),
       m.first_name,
       a.start_time,
       a.status,
       b.total_price,
       b.balance_due
FROM appointments a
JOIN clients c ON c.id = a.client_id
JOIN masters m ON m.id = a.master_id
JOIN v_appointment_balance b ON b.appointment_id = a.id
{where}
ORDER BY a.start_time
"""

HEADERS = ["Клиент", "Мастер", "Время", "Статус", "Стоимость", "Остаток"]

STATUSES = {
    "scheduled": "Запланирована",
    "completed": "Выполнена",
    "cancelled": "Отменена",
    "no_show": "Не пришла",
}


class AppointmentsTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user

        add_button = QPushButton("Новая запись")
        add_button.clicked.connect(self.open_new_appointment)
        cancel_button = QPushButton("Отменить запись")
        cancel_button.clicked.connect(self.cancel_appointment)
        pay_button = QPushButton("Отметить оплату")
        pay_button.clicked.connect(self.add_payment)

        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(cancel_button)
        buttons.addWidget(pay_button)

        if user["role"] == "client":
            pay_button.hide()

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self.table)

        self.load_appointments()

    def load_appointments(self):
        role = self.user["role"]
        if role == "master":
            where, params = "WHERE a.master_id = %s", (self.user["master_id"],)
        elif role == "client":
            where, params = "WHERE a.client_id = %s", (self.user["client_id"],)
        else:
            where, params = "", ()

        with get_connection() as conn:
            rows = conn.execute(QUERY.format(where=where), params).fetchall()

        self.table.setColumnCount(len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setRowCount(len(rows))

        for r, (app_id, client, master, start, status, total, due) in enumerate(rows):
            values = [client, master, start.strftime("%d.%m.%Y %H:%M"),
                      STATUSES.get(status, status), f"{total:.2f}", f"{due:.2f}"]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))

            self.table.item(r, 0).setData(
                Qt.ItemDataRole.UserRole, (app_id, status, due)
            )

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def selected_appointment(self):
        """Возвращает (id, статус, остаток) выбранной записи или None."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Выберите запись",
                                    "Сначала выберите запись в таблице.")
            return None
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def open_new_appointment(self):
        role = self.user["role"]
        master_id = self.user["master_id"] if role == "master" else None
        client_id = self.user["client_id"] if role == "client" else None
        dialog = AppointmentDialog(self, master_id, client_id)
        if dialog.exec():
            self.load_appointments()

    def cancel_appointment(self):
        selected = self.selected_appointment()
        if selected is None:
            return
        app_id, status, _ = selected

        if status != "scheduled":
            QMessageBox.information(self, "Нельзя отменить",
                                    "Отменить можно только запланированную запись.")
            return

        answer = QMessageBox.question(self, "Отмена записи",
                                      "Отменить выбранную запись?")
        if answer != QMessageBox.StandardButton.Yes:
            return

        with get_connection() as conn:
            conn.execute(
                "UPDATE appointments SET status = 'cancelled' WHERE id = %s",
                (app_id,),
            )
        self.load_appointments()

    def add_payment(self):
        selected = self.selected_appointment()
        if selected is None:
            return
        app_id, status, due = selected

        if status == "cancelled":
            QMessageBox.information(self, "Запись отменена",
                                    "Для отменённой записи оплата не принимается.")
            return
        if due <= 0:
            QMessageBox.information(self, "Уже оплачено",
                                    "По этой записи нет задолженности.")
            return

        dialog = PaymentDialog(app_id, due, self.user["id"], self)
        if dialog.exec():
            self.load_appointments()


class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.setWindowTitle(f"Студия красоты, вы вошли как {user['username']}")
        self.resize(1100, 500)

        self.appointments_tab = AppointmentsTab(user)
        self.clients_tab = None
        self.reports_tab = None

        self.tabs = QTabWidget()
        self.tabs.addTab(self.appointments_tab, "Записи")
        if user["role"] in ("admin", "master"):
            self.clients_tab = ClientsTab()
            self.tabs.addTab(self.clients_tab, "Клиенты")
        if user["role"] == "admin":
            self.reports_tab = ReportsTab()
            self.tabs.addTab(self.reports_tab, "Отчёты")
        self.tabs.currentChanged.connect(self.refresh_tab)
        self.setCentralWidget(self.tabs)

    def refresh_tab(self, index):
        """При переходе на вкладку обновляем её данные."""
        widget = self.tabs.widget(index)
        if widget is self.appointments_tab:
            self.appointments_tab.load_appointments()
        elif widget is self.clients_tab:
            self.clients_tab.load_clients()
        elif widget is self.reports_tab:
            self.reports_tab.show_report()


app = QApplication(sys.argv)

login = LoginDialog()
if login.exec() != QDialog.DialogCode.Accepted:
    sys.exit(0)

window = MainWindow(login.user)
window.show()
sys.exit(app.exec())