import csv
from datetime import date
from decimal import Decimal

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from db import get_connection

REVENUE = """
SELECT paid_at::date AS day, COUNT(*) AS payments_count, SUM(amount) AS total
FROM payments
WHERE paid_at::date BETWEEN %s AND %s
GROUP BY day
ORDER BY day
"""

POPULAR_SERVICES = """
SELECT s.name, COUNT(*) AS times_booked, SUM(aps.price_at_booking) AS revenue
FROM appointment_services aps
JOIN appointments a ON a.id = aps.appointment_id
JOIN services s ON s.id = aps.service_id
WHERE a.status IN ('scheduled', 'completed')
  AND a.start_time::date BETWEEN %s AND %s
GROUP BY s.id, s.name
ORDER BY times_booked DESC, revenue DESC
"""

MASTER_LOAD = """
SELECT m.first_name,
       COUNT(a.id) AS appointments_count,
       COALESCE(ROUND(SUM(EXTRACT(EPOCH FROM (a.end_time - a.start_time)) / 3600), 1), 0)
FROM masters m
LEFT JOIN appointments a
       ON a.master_id = m.id
      AND a.status IN ('scheduled', 'completed')
      AND a.start_time::date BETWEEN %s AND %s
GROUP BY m.id, m.first_name
ORDER BY appointments_count DESC, m.first_name
"""

REPORTS = {
    "Выручка по дням (по оплатам)": (["Дата", "Платежей", "Сумма"], REVENUE, 2),
    "Популярные услуги": (["Услуга", "Записей", "Сумма"], POPULAR_SERVICES, 2),
    "Загрузка мастеров": (["Мастер", "Записей", "Часов"], MASTER_LOAD, None),
}


def fmt(value):
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


class ReportsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.headers = []
        self.rows = []

        self.report_box = QComboBox()
        self.report_box.addItems(REPORTS.keys())

        self.date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_to = QDateEdit(QDate.currentDate().addDays(30))
        for edit in (self.date_from, self.date_to):
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("dd.MM.yyyy")

        show_button = QPushButton("Показать")
        show_button.clicked.connect(self.show_report)
        export_button = QPushButton("Экспорт в CSV")
        export_button.clicked.connect(self.export_csv)

        top = QHBoxLayout()
        top.addWidget(self.report_box)
        top.addWidget(QLabel("с"))
        top.addWidget(self.date_from)
        top.addWidget(QLabel("по"))
        top.addWidget(self.date_to)
        top.addWidget(show_button)
        top.addWidget(export_button)

        self.summary = QLabel("")
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(self.summary)

        self.show_report()

    def refresh(self):
        self.show_report()

    def show_report(self):
        headers, query, total_column = REPORTS[self.report_box.currentText()]
        start = self.date_from.date().toPyDate()
        end = self.date_to.date().toPyDate()

        if start > end:
            self.summary.setText("Дата начала позже даты окончания.")
            return

        with get_connection() as conn:
            rows = conn.execute(query, (start, end)).fetchall()
        self.headers, self.rows = headers, rows

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(fmt(value)))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        if not rows:
            self.summary.setText("За выбранный период данных нет.")
        elif total_column is not None:
            total = sum(row[total_column] for row in rows)
            self.summary.setText(f"Итого: {total:.2f} ₽")
        else:
            self.summary.setText("")

    def export_csv(self):
        if not self.rows:
            QMessageBox.information(self, "Нет данных", "Сначала постройте отчёт.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт", "report.csv", "CSV (*.csv)"
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(self.headers)
            for row in self.rows:
                writer.writerow([
                    fmt(v).replace(".", ",") if isinstance(v, Decimal) else fmt(v)
                    for v in row
                ])
        QMessageBox.information(self, "Готово", "Отчёт сохранён.")