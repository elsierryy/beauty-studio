from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from client_dialog import ClientDialog
from db import get_connection

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

        add_button = QPushButton("Добавить клиента")
        add_button.clicked.connect(self.add_client)
        edit_button = QPushButton("Изменить")
        edit_button.clicked.connect(self.edit_client)

        top = QHBoxLayout()
        top.addWidget(self.search)
        top.addWidget(add_button)
        top.addWidget(edit_button)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_client)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)

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
            # все данные клиента прячем в первую ячейку для окна редактирования
            self.table.item(r, 0).setData(Qt.ItemDataRole.UserRole, row)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def add_client(self):
        if ClientDialog(parent=self).exec():
            self.load_clients()

    def edit_client(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Выберите клиента",
                                    "Сначала выберите клиента в таблице.")
            return
        client = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if ClientDialog(client, self).exec():
            self.load_clients()