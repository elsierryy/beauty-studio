from datetime import datetime

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from appointment_dialog import AppointmentDialog
from constants import STATUSES
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
{where}
ORDER BY a.start_time
"""

HEADERS = ["Клиент", "Мастер", "Время", "Статус", "Стоимость", "Остаток"]


class AppointmentsTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        role = user["role"]

        buttons = QHBoxLayout()
        for text, handler, roles in (
            ("Новая запись", self.open_new_appointment, ("admin", "master", "client")),
            ("Отменить запись", self.cancel_appointment, ("admin", "master", "client")),
            ("Отметить оплату", self.add_payment, ("admin", "master")),
            ("Выполнена", lambda: self.set_status("completed"), ("admin", "master")),
            ("Не пришла", lambda: self.set_status("no_show"), ("admin", "master")),
        ):
            if role in roles:
                button = QPushButton(text)
                button.clicked.connect(handler)
                buttons.addWidget(button)

        self.master_filter = QComboBox()
        self.master_filter.addItem("Все мастера", None)
        if role == "master":
            self.master_filter.hide()
        else:
            with get_connection() as conn:
                for master_id, name in conn.execute(
                    "SELECT id, first_name FROM masters ORDER BY first_name"
                ):
                    self.master_filter.addItem(name, master_id)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Все статусы", None)
        for code, title in STATUSES.items():
            self.status_filter.addItem(title, code)

        self.date_check = QCheckBox("Период:")
        self.date_from = QDateEdit(QDate.currentDate())
        self.date_to = QDateEdit(QDate.currentDate().addDays(30))
        for edit in (self.date_from, self.date_to):
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("dd.MM.yyyy")

        filters = QHBoxLayout()
        filters.addWidget(self.master_filter)
        filters.addWidget(self.status_filter)
        filters.addWidget(self.date_check)
        filters.addWidget(self.date_from)
        filters.addWidget(QLabel("по"))
        filters.addWidget(self.date_to)
        filters.addStretch()

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addLayout(filters)
        layout.addWidget(self.table)

        self.master_filter.currentIndexChanged.connect(self.load_appointments)
        self.status_filter.currentIndexChanged.connect(self.load_appointments)
        self.date_check.toggled.connect(self.load_appointments)
        self.date_from.dateChanged.connect(self.load_appointments)
        self.date_to.dateChanged.connect(self.load_appointments)

        self.load_appointments()

    def refresh(self):
        self.load_appointments()

    def load_appointments(self):
        role = self.user["role"]
        conditions, params = [], []

        if role == "master":
            conditions.append("a.master_id = %s")
            params.append(self.user["master_id"])
        elif role == "client":
            conditions.append("a.client_id = %s")
            params.append(self.user["client_id"])

        if self.master_filter.currentData() is not None:
            conditions.append("a.master_id = %s")
            params.append(self.master_filter.currentData())
        if self.status_filter.currentData() is not None:
            conditions.append("a.status = %s")
            params.append(self.status_filter.currentData())
        if self.date_check.isChecked():
            conditions.append("a.start_time::date BETWEEN %s AND %s")
            params += [self.date_from.date().toPyDate(),
                       self.date_to.date().toPyDate()]

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
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
                Qt.ItemDataRole.UserRole, (app_id, status, due, start)
            )

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def selected_appointment(self):
        """Возвращает (id, статус, остаток, начало) выбранной записи или None."""
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
        if AppointmentDialog(self, master_id, client_id).exec():
            self.load_appointments()

    def cancel_appointment(self):
        selected = self.selected_appointment()
        if selected is None:
            return
        app_id, status, _, _ = selected

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

    def set_status(self, new_status):
        selected = self.selected_appointment()
        if selected is None:
            return
        app_id, status, _, start = selected

        if status != "scheduled":
            QMessageBox.information(
                self, "Нельзя изменить",
                "Статус можно менять только у запланированной записи.")
            return
        if start > datetime.now().astimezone():
            QMessageBox.information(self, "Рано",
                                    "Эта запись ещё не наступила.")
            return

        with get_connection() as conn:
            conn.execute(
                "UPDATE appointments SET status = %s WHERE id = %s",
                (new_status, app_id),
            )
        self.load_appointments()

    def add_payment(self):
        selected = self.selected_appointment()
        if selected is None:
            return
        app_id, status, due, _ = selected

        if status == "cancelled":
            QMessageBox.information(self, "Запись отменена",
                                    "Для отменённой записи оплата не принимается.")
            return
        if due <= 0:
            QMessageBox.information(self, "Уже оплачено",
                                    "По этой записи нет задолженности.")
            return

        if PaymentDialog(app_id, due, self.user["id"], self).exec():
            self.load_appointments()