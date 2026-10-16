from datetime import datetime, timedelta
from decimal import Decimal

import psycopg
from PyQt6.QtCore import QDate, QDateTime, QTime, Qt
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QListWidget, QListWidgetItem, QMessageBox,
)

from db import get_connection

DATE_FORMAT = "dd.MM.yyyy HH:mm"


class AppointmentDialog(QDialog):
    def __init__(self, parent=None, master_id=None, client_id=None):
        super().__init__(parent)
        self.fixed_client_id = client_id
        self.setWindowTitle("Новая запись")
        self.resize(450, 420)

        self.client_box = QComboBox()
        self.master_box = QComboBox()
        self.services_list = QListWidget()

        self.date_edit = QDateEdit(QDate.currentDate().addDays(1))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")

        self.time_box = QComboBox()
        for hour in range(8, 22):
            for minute in (0, 15, 30, 45):
                self.time_box.addItem(f"{hour:02d}:{minute:02d}", QTime(hour, minute))
        self.time_box.setCurrentText("10:00")

        self.total_label = QLabel("0.00 ₽")
        self.end_label = QLabel("-")

        form = QFormLayout(self)
        form.addRow("Клиент:", self.client_box)
        form.addRow("Мастер:", self.master_box)
        form.addRow("Услуги:", self.services_list)
        form.addRow("Дата:", self.date_edit)
        form.addRow("Время:", self.time_box)
        form.addRow("Окончание:", self.end_label)
        form.addRow("Итого:", self.total_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.load_lists()

        if master_id is not None:
            self.master_box.setCurrentIndex(self.master_box.findData(master_id))
            self.master_box.setEnabled(False)
        if client_id is not None:
            self.client_box.setEnabled(False)

        # сигналы подключаем после первой загрузки, чтобы они не сработали раньше времени
        self.master_box.currentIndexChanged.connect(self.load_services)
        self.services_list.itemChanged.connect(self.update_summary)
        self.date_edit.dateChanged.connect(self.update_summary)
        self.time_box.currentIndexChanged.connect(self.update_summary)

        self.load_services()

    def start_qdatetime(self):
        """Собирает начало записи из выбранной даты и времени."""
        return QDateTime(self.date_edit.date(), self.time_box.currentData())

    def load_lists(self):
        with get_connection() as conn:
            if self.fixed_client_id is None:
                clients = conn.execute(
                    "SELECT id, first_name || ' ' || COALESCE(last_name, '') "
                    "FROM clients ORDER BY first_name"
                ).fetchall()
            else:
                clients = conn.execute(
                    "SELECT id, first_name || ' ' || COALESCE(last_name, '') "
                    "FROM clients WHERE id = %s",
                    (self.fixed_client_id,),
                ).fetchall()
            masters = conn.execute(
                "SELECT id, first_name FROM masters "
                "WHERE is_active ORDER BY first_name"
            ).fetchall()

        for client_id, name in clients:
            self.client_box.addItem(name, client_id)
        for master_id, name in masters:
            self.master_box.addItem(name, master_id)

    def load_services(self):
        """Показывает только те услуги, которые делает выбранный мастер."""
        master_id = self.master_box.currentData()
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.id, s.name, s.price, s.duration_minutes
                FROM services s
                JOIN master_services ms ON ms.service_id = s.id
                WHERE ms.master_id = %s AND s.is_active
                ORDER BY s.name
                """,
                (master_id,),
            ).fetchall()

        self.services_list.blockSignals(True)
        self.services_list.clear()
        for service_id, name, price, minutes in rows:
            item = QListWidgetItem(f"{name} - {price:.2f} ₽, {minutes} мин")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, (service_id, price, minutes))
            self.services_list.addItem(item)
        self.services_list.blockSignals(False)

        self.update_summary()

    def update_summary(self):
        """Считает общую цену и время окончания по отмеченным услугам."""
        total = Decimal(0)
        minutes = 0
        for i in range(self.services_list.count()):
            item = self.services_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                _, price, duration = item.data(Qt.ItemDataRole.UserRole)
                total += price
                minutes += duration

        self.total_label.setText(f"{total:.2f} ₽")

        if minutes:
            end = self.start_qdatetime().addSecs(minutes * 60)
            self.end_label.setText(f"{end.toString(DATE_FORMAT)} ({minutes} мин)")
        else:
            self.end_label.setText("-")

    def within_schedule(self, start, end):
        """Проверяет, что запись целиком попадает в рабочие часы мастера."""
        master_id = self.master_box.currentData()
        weekday = start.isoweekday()  # 1 = понедельник ... 7 = воскресенье

        with get_connection() as conn:
            row = conn.execute(
                "SELECT start_time, end_time FROM master_schedules "
                "WHERE master_id = %s AND weekday = %s",
                (master_id, weekday),
            ).fetchone()

        if row is None:
            QMessageBox.warning(self, "Выходной", "В этот день мастер не работает.")
            return False

        work_start, work_end = row
        if (end.date() != start.date()
                or start.time() < work_start
                or end.time() > work_end):
            QMessageBox.warning(
                self, "Вне рабочего времени",
                f"Мастер работает с {work_start:%H:%M} до {work_end:%H:%M}. "
                "Запись должна целиком попадать в это время.",
            )
            return False

        return True

    def save(self):
        """Сохраняет запись и её услуги в базу одной транзакцией."""
        services = []
        for i in range(self.services_list.count()):
            item = self.services_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                services.append(item.data(Qt.ItemDataRole.UserRole))

        if not services:
            QMessageBox.warning(self, "Нет услуг", "Отметьте хотя бы одну услугу.")
            return

        minutes = sum(duration for _, _, duration in services)
        start = self.start_qdatetime().toPyDateTime().astimezone()
        end = start + timedelta(minutes=minutes)

        if start < datetime.now().astimezone():
            QMessageBox.warning(self, "Неверное время", "Нельзя записать в прошлое.")
            return

        if not self.within_schedule(start, end):
            return

        try:
            with get_connection() as conn:
                appointment_id = conn.execute(
                    """
                    INSERT INTO appointments (client_id, master_id, start_time, end_time)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (self.client_box.currentData(), self.master_box.currentData(),
                     start, end),
                ).fetchone()[0]

                for service_id, price, _ in services:
                    conn.execute(
                        """
                        INSERT INTO appointment_services
                            (appointment_id, service_id, price_at_booking)
                        VALUES (%s, %s, %s)
                        """,
                        (appointment_id, service_id, price),
                    )
        except psycopg.errors.ExclusionViolation:
            QMessageBox.warning(
                self, "Время занято",
                "У этого мастера уже есть запись на это время. Выберите другое.",
            )
            return

        self.accept()