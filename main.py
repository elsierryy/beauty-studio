import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QHBoxLayout, QHeaderView, QMainWindow,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from appointment_dialog import AppointmentDialog
from db import get_connection
from payment_dialog import PaymentDialog

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
ORDER BY a.start_time
"""

HEADERS = ["Клиент", "Мастер", "Время", "Статус", "Стоимость", "Остаток"]

STATUSES = {
    "scheduled": "Запланирована",
    "completed": "Выполнена",
    "cancelled": "Отменена",
    "no_show": "Не пришла",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Студия красоты")
        self.resize(950, 450)

        self.add_button = QPushButton("Новая запись")
        self.add_button.clicked.connect(self.open_new_appointment)
        self.cancel_button = QPushButton("Отменить запись")
        self.cancel_button.clicked.connect(self.cancel_appointment)
        self.pay_button = QPushButton("Отметить оплату")
        self.pay_button.clicked.connect(self.add_payment)

        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.pay_button)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout()
        layout.addLayout(buttons)
        layout.addWidget(self.table)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.load_appointments()

    def load_appointments(self):
        with get_connection() as conn:
            rows = conn.execute(QUERY).fetchall()

        self.table.setColumnCount(len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setRowCount(len(rows))

        for r, (app_id, client, master, start, status, total, due) in enumerate(rows):
            values = [client, master, start.strftime("%d.%m.%Y %H:%M"),
                      STATUSES.get(status, status), f"{total:.2f}", f"{due:.2f}"]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))

            # прячем служебные данные в первую ячейку строки
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
        dialog = AppointmentDialog(self)
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

        dialog = PaymentDialog(app_id, due, self)
        if dialog.exec():
            self.load_appointments()


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())