from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from catalog_dialogs import (
    MasterDialog, MasterServicesDialog, ScheduleDialog, ServiceDialog,
)
from db import get_connection


class DataPanel(QWidget):
    headers = []
    query = ""

    def __init__(self):
        super().__init__()
        self.buttons = QHBoxLayout()
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addLayout(self.buttons)
        layout.addWidget(self.table)

    def add_button(self, text, handler):
        button = QPushButton(text)
        button.clicked.connect(handler)
        self.buttons.addWidget(button)

    def refresh(self):
        with get_connection() as conn:
            rows = conn.execute(self.query).fetchall()

        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(self.display(row)):
                self.table.setItem(r, c, QTableWidgetItem(value))
            self.table.item(r, 0).setData(Qt.ItemDataRole.UserRole, row)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Выберите строку",
                                    "Сначала выберите строку в таблице.")
            return None
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)


class ServicesPanel(DataPanel):
    headers = ["Категория", "Услуга", "Цена", "Длительность", "Доступна"]
    query = """
        SELECT s.id, c.name, s.name, s.price, s.duration_minutes, s.is_active
        FROM services s
        JOIN service_categories c ON c.id = s.category_id
        ORDER BY c.name, s.name
    """

    def __init__(self):
        super().__init__()
        self.add_button("Добавить", self.add)
        self.add_button("Изменить", self.edit)
        self.add_button("Включить или выключить", self.toggle)
        self.refresh()

    def display(self, row):
        _, category, name, price, minutes, active = row
        return [category, name, f"{price:.2f}", f"{minutes} мин",
                "Да" if active else "Нет"]

    def add(self):
        if ServiceDialog(parent=self).exec():
            self.refresh()

    def edit(self):
        service = self.selected()
        if service and ServiceDialog(service, self).exec():
            self.refresh()

    def toggle(self):
        service = self.selected()
        if service is None:
            return
        with get_connection() as conn:
            conn.execute(
                "UPDATE services SET is_active = NOT is_active WHERE id = %s",
                (service[0],),
            )
        self.refresh()


class MastersPanel(DataPanel):
    headers = ["Мастер", "Телефон", "Работает"]
    query = ("SELECT id, first_name, last_name, phone, is_active "
             "FROM masters ORDER BY first_name")

    def __init__(self):
        super().__init__()
        self.add_button("Добавить", self.add)
        self.add_button("Изменить", self.edit)
        self.add_button("Включить или выключить", self.toggle)
        self.add_button("Услуги мастера", self.services)
        self.add_button("График работы", self.schedule)
        self.refresh()

    def display(self, row):
        _, first, last, phone, active = row
        return [f"{first} {last or ''}".strip(), phone or "",
                "Да" if active else "Нет"]

    def add(self):
        if MasterDialog(parent=self).exec():
            self.refresh()

    def edit(self):
        master = self.selected()
        if master and MasterDialog(master, self).exec():
            self.refresh()

    def toggle(self):
        master = self.selected()
        if master is None:
            return
        with get_connection() as conn:
            conn.execute(
                "UPDATE masters SET is_active = NOT is_active WHERE id = %s",
                (master[0],),
            )
        self.refresh()

    def services(self):
        master = self.selected()
        if master:
            MasterServicesDialog(master[0], master[1], self).exec()

    def schedule(self):
        master = self.selected()
        if master:
            ScheduleDialog(master[0], master[1], self).exec()


class CatalogTab(QTabWidget):
    def __init__(self):
        super().__init__()
        self.addTab(ServicesPanel(), "Услуги")
        self.addTab(MastersPanel(), "Мастера")

    def refresh(self):
        for i in range(self.count()):
            self.widget(i).refresh()