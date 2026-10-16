import sys
from PyQt6.QtWidgets import (
    QApplication, QHeaderView, QMainWindow, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from appointment_dialog import AppointmentDialog
from db import get_connection

QUERY = """
SELECT c.first_name || ' ' || COALESCE(c.last_name, ''),
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Студия красоты")
        self.resize(900, 400)

        self.add_button = QPushButton("Новая запись")
        self.add_button.clicked.connect(self.open_new_appointment)

        self.table = QTableWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.add_button)
        layout.addWidget(self.table)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.load_appointments()

    def open_new_appointment(self):
        dialog = AppointmentDialog(self)
        if dialog.exec():
            self.load_appointments()

    def load_appointments(self):
        with get_connection() as conn:
            rows = conn.execute(QUERY).fetchall()

        self.table.setColumnCount(len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setRowCount(len(rows))

        for r, (client, master, start, status, total, due) in enumerate(rows):
            values = [client, master, start.strftime("%d.%m.%Y %H:%M"),
                      status, f"{total:.2f}", f"{due:.2f}"]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())