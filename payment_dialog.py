from decimal import Decimal

from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel,
)

from db import get_connection

METHODS = [("Наличные", "cash"), ("Карта", "card"), ("Перевод", "transfer")]


class PaymentDialog(QDialog):
    def __init__(self, appointment_id, balance_due, parent=None):
        super().__init__(parent)
        self.appointment_id = appointment_id
        self.setWindowTitle("Оплата")

        self.amount_box = QDoubleSpinBox()
        self.amount_box.setDecimals(2)
        self.amount_box.setRange(0.01, float(balance_due))
        self.amount_box.setValue(float(balance_due))
        self.amount_box.setSuffix(" ₽")

        self.method_box = QComboBox()
        for title, code in METHODS:
            self.method_box.addItem(title, code)

        form = QFormLayout(self)
        form.addRow("К оплате:", QLabel(f"{balance_due:.2f} ₽"))
        form.addRow("Сумма:", self.amount_box)
        form.addRow("Способ:", self.method_box)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def save(self):
        amount = Decimal(f"{self.amount_box.value():.2f}")
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO payments (appointment_id, amount, method) "
                "VALUES (%s, %s, %s)",
                (self.appointment_id, amount, self.method_box.currentData()),
            )
        self.accept()