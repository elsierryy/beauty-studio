from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHeaderView, QLabel, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from constants import STATUSES
from db import get_connection

QUERY = """
SELECT a.start_time,
       m.first_name,
       a.status,
       COALESCE(string_agg(s.name, ', ' ORDER BY s.name), ''),
       b.total_price,
       b.total_paid
FROM appointments a
JOIN masters m ON m.id = a.master_id
JOIN v_appointment_balance b ON b.appointment_id = a.id
LEFT JOIN appointment_services aps ON aps.appointment_id = a.id
LEFT JOIN services s ON s.id = aps.service_id
WHERE a.client_id = %s
GROUP BY a.id, m.first_name, b.total_price, b.total_paid
ORDER BY a.start_time DESC
"""

HEADERS = ["Дата", "Мастер", "Статус", "Услуги", "Стоимость", "Оплачено"]


class HistoryDialog(QDialog):
    def __init__(self, client_id, client_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"История: {client_name}")
        self.resize(950, 400)

        with get_connection() as conn:
            rows = conn.execute(QUERY, (client_id,)).fetchall()

        table = QTableWidget(len(rows), len(HEADERS))
        table.setHorizontalHeaderLabels(HEADERS)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for r, (start, master, status, services, total, paid) in enumerate(rows):
            values = [start.strftime("%d.%m.%Y %H:%M"), master,
                      STATUSES.get(status, status), services,
                      f"{total:.2f}", f"{paid:.2f}"]
            for c, value in enumerate(values):
                table.setItem(r, c, QTableWidgetItem(value))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        total_paid = sum(row[5] for row in rows)
        summary = QLabel(f"Записей: {len(rows)}. Оплачено всего: {total_paid:.2f} ₽")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(table)
        layout.addWidget(summary)
        layout.addWidget(buttons)