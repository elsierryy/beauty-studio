from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from client_dialog import ClientDialog
from db import get_connection
from history_dialog import HistoryDialog

QUERY = """
SELECT id, first_name, last_name, phone, email, notes
FROM clients
WHERE first_name ILIKE %s
   OR COALESCE(last_name, '') ILIKE %s
   OR phone LIKE %s
ORDER BY first_name, last_name
"""

HEADERS = ["Имя", "Телефон", "Email", "Заметки"]


class ClientsTab(QWidget):
    def __init__(self):
        super().__init__()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по имени или телефону")
        self.search.textChanged.connect(self.load_clients)

        top = QHBoxLayout()
        top.addWidget(self.search)
        for text, handler in (
            ("Добавить клиента", self.add_client),
            ("Изменить", self.edit_client),
            ("История записей", self.show_history),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            top.addWidget(button)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_client)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)

        self.load_clients()

    def refresh(self):
        self.load_clients()

    def load_clients(self):
        pattern = f"%{self.search.text().strip()}%"
        with get_connection() as conn:
            rows = conn.execute(QUERY, (pattern, pattern, pattern)).fetchall()

        self.table.setColumnCount(len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            _, first, last, phone, email, notes = row
            values = [f"{first} {last or ''}".strip(), phone, email or "", notes or ""]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(value))
            self.table.item(r, 0).setData(Qt.ItemDataRole.UserRole, row)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def selected_client(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Выберите клиента",
                                    "Сначала выберите клиента в таблице.")
            return None
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def add_client(self):
        if ClientDialog(parent=self).exec():
            self.load_clients()

    def edit_client(self):
        client = self.selected_client()
        if client and ClientDialog(client, self).exec():
            self.load_clients()

    def show_history(self):
        client = self.selected_client()
        if client:
            name = f"{client[1]} {client[2] or ''}".strip()
            HistoryDialog(client[0], name, self).exec()