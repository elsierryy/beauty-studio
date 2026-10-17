from datetime import datetime
from decimal import Decimal

import psycopg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QGridLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QSpinBox, QVBoxLayout,
)

from db import get_connection

DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница",
        "Суббота", "Воскресенье"]


def save_cancel(dialog, on_save):
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save
        | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(on_save)
    buttons.rejected.connect(dialog.reject)
    return buttons


class ServiceDialog(QDialog):
    """service = (id, категория, название, цена, минуты, активна) или None."""

    def __init__(self, service=None, parent=None):
        super().__init__(parent)
        self.service_id = service[0] if service else None
        self.setWindowTitle("Изменение услуги" if service else "Новая услуга")

        self.category_box = QComboBox()
        self.category_box.setEditable(True)
        with get_connection() as conn:
            for (name,) in conn.execute(
                "SELECT name FROM service_categories ORDER BY name"
            ):
                self.category_box.addItem(name)

        self.name = QLineEdit()
        self.price = QDoubleSpinBox()
        self.price.setRange(0, 1000000)
        self.price.setDecimals(2)
        self.price.setSuffix(" ₽")
        self.minutes = QSpinBox()
        self.minutes.setRange(5, 480)
        self.minutes.setSingleStep(5)
        self.minutes.setSuffix(" мин")
        self.minutes.setValue(60)
        self.active = QCheckBox("Доступна для записи")
        self.active.setChecked(True)

        if service:
            _, category, name, price, minutes, active = service
            self.category_box.setCurrentText(category)
            self.name.setText(name)
            self.price.setValue(float(price))
            self.minutes.setValue(minutes)
            self.active.setChecked(active)

        form = QFormLayout(self)
        form.addRow("Категория:", self.category_box)
        form.addRow("Название:", self.name)
        form.addRow("Цена:", self.price)
        form.addRow("Длительность:", self.minutes)
        form.addRow("", self.active)
        form.addRow(save_cancel(self, self.save))

    def save(self):
        category = self.category_box.currentText().strip()
        name = self.name.text().strip()
        if not category or not name:
            QMessageBox.warning(self, "Ошибка", "Укажите категорию и название.")
            return
        price = Decimal(f"{self.price.value():.2f}")

        try:
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM service_categories WHERE name = %s", (category,)
                ).fetchone()
                if row:
                    category_id = row[0]
                else:
                    category_id = conn.execute(
                        "INSERT INTO service_categories (name) VALUES (%s) RETURNING id",
                        (category,),
                    ).fetchone()[0]

                values = (category_id, name, price, self.minutes.value(),
                          self.active.isChecked())
                if self.service_id is None:
                    conn.execute(
                        "INSERT INTO services "
                        "(category_id, name, price, duration_minutes, is_active) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        values,
                    )
                else:
                    conn.execute(
                        "UPDATE services SET category_id = %s, name = %s, "
                        "price = %s, duration_minutes = %s, is_active = %s "
                        "WHERE id = %s",
                        values + (self.service_id,),
                    )
        except psycopg.errors.UniqueViolation:
            QMessageBox.warning(self, "Дубликат",
                                "В этой категории уже есть такая услуга.")
            return
        self.accept()


class MasterDialog(QDialog):
    """master = (id, имя, фамилия, телефон, активен) или None."""

    def __init__(self, master=None, parent=None):
        super().__init__(parent)
        self.master_id = master[0] if master else None
        self.setWindowTitle("Изменение мастера" if master else "Новый мастер")

        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.phone = QLineEdit()
        self.active = QCheckBox("Работает")
        self.active.setChecked(True)

        if master:
            _, first, last, phone, active = master
            self.first_name.setText(first)
            self.last_name.setText(last or "")
            self.phone.setText(phone or "")
            self.active.setChecked(active)

        form = QFormLayout(self)
        form.addRow("Имя:", self.first_name)
        form.addRow("Фамилия:", self.last_name)
        form.addRow("Телефон:", self.phone)
        form.addRow("", self.active)
        form.addRow(save_cancel(self, self.save))

    def save(self):
        first = self.first_name.text().strip()
        if not first:
            QMessageBox.warning(self, "Ошибка", "Укажите имя мастера.")
            return
        values = (first, self.last_name.text().strip() or None,
                  self.phone.text().strip() or None, self.active.isChecked())

        with get_connection() as conn:
            if self.master_id is None:
                conn.execute(
                    "INSERT INTO masters (first_name, last_name, phone, is_active) "
                    "VALUES (%s, %s, %s, %s)",
                    values,
                )
            else:
                conn.execute(
                    "UPDATE masters SET first_name = %s, last_name = %s, "
                    "phone = %s, is_active = %s WHERE id = %s",
                    values + (self.master_id,),
                )
        self.accept()


class MasterServicesDialog(QDialog):
    def __init__(self, master_id, master_name, parent=None):
        super().__init__(parent)
        self.master_id = master_id
        self.setWindowTitle(f"Услуги мастера: {master_name}")
        self.resize(400, 400)

        with get_connection() as conn:
            services = conn.execute(
                "SELECT s.id, c.name, s.name FROM services s "
                "JOIN service_categories c ON c.id = s.category_id "
                "WHERE s.is_active ORDER BY c.name, s.name"
            ).fetchall()
            chosen = {
                row[0] for row in conn.execute(
                    "SELECT service_id FROM master_services WHERE master_id = %s",
                    (master_id,),
                )
            }

        self.list = QListWidget()
        for service_id, category, name in services:
            item = QListWidgetItem(f"{category}: {name}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if service_id in chosen
                else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, service_id)
            self.list.addItem(item)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Отметьте услуги, которые делает мастер:"))
        layout.addWidget(self.list)
        layout.addWidget(save_cancel(self, self.save))

    def save(self):
        listed, checked = [], []
        for i in range(self.list.count()):
            item = self.list.item(i)
            service_id = item.data(Qt.ItemDataRole.UserRole)
            listed.append(service_id)
            if item.checkState() == Qt.CheckState.Checked:
                checked.append(service_id)

        with get_connection() as conn:
            conn.execute(
                "DELETE FROM master_services "
                "WHERE master_id = %s AND service_id = ANY(%s)",
                (self.master_id, listed),
            )
            for service_id in checked:
                conn.execute(
                    "INSERT INTO master_services (master_id, service_id) "
                    "VALUES (%s, %s)",
                    (self.master_id, service_id),
                )
        self.accept()


def time_box():
    box = QComboBox()
    for hour in range(6, 24):
        for minute in (0, 15, 30, 45):
            box.addItem(f"{hour:02d}:{minute:02d}")
    return box


class ScheduleDialog(QDialog):
    def __init__(self, master_id, master_name, parent=None):
        super().__init__(parent)
        self.master_id = master_id
        self.setWindowTitle(f"График: {master_name}")

        with get_connection() as conn:
            existing = {
                weekday: (start, end) for weekday, start, end in conn.execute(
                    "SELECT weekday, start_time, end_time "
                    "FROM master_schedules WHERE master_id = %s",
                    (master_id,),
                )
            }

        grid = QGridLayout()
        self.rows = []
        for weekday, day in enumerate(DAYS, start=1):
            check = QCheckBox(day)
            start, end = time_box(), time_box()
            if weekday in existing:
                check.setChecked(True)
                start.setCurrentText(f"{existing[weekday][0]:%H:%M}")
                end.setCurrentText(f"{existing[weekday][1]:%H:%M}")
            else:
                start.setCurrentText("10:00")
                end.setCurrentText("19:00")
            row = weekday - 1
            grid.addWidget(check, row, 0)
            grid.addWidget(start, row, 1)
            grid.addWidget(QLabel("до"), row, 2)
            grid.addWidget(end, row, 3)
            self.rows.append((weekday, check, start, end))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Отметьте рабочие дни и часы работы:"))
        layout.addLayout(grid)
        layout.addWidget(save_cancel(self, self.save))

    def save(self):
        schedule = []
        for weekday, check, start, end in self.rows:
            if not check.isChecked():
                continue
            s = datetime.strptime(start.currentText(), "%H:%M").time()
            e = datetime.strptime(end.currentText(), "%H:%M").time()
            if e <= s:
                QMessageBox.warning(
                    self, "Ошибка",
                    f"{DAYS[weekday - 1]}: конец должен быть позже начала.",
                )
                return
            schedule.append((weekday, s, e))

        with get_connection() as conn:
            conn.execute(
                "DELETE FROM master_schedules WHERE master_id = %s",
                (self.master_id,),
            )
            for weekday, s, e in schedule:
                conn.execute(
                    "INSERT INTO master_schedules "
                    "(master_id, weekday, start_time, end_time) "
                    "VALUES (%s, %s, %s, %s)",
                    (self.master_id, weekday, s, e),
                )
        self.accept()