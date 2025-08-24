import sys
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QLabel, QListWidget, QListWidgetItem, QStackedLayout
)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt

API_URL = "http://127.0.0.1:8000/api/products/"


class AdminPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🛒 لوحة التحكم")
        self.resize(1000, 600)
        self.init_ui()

    def init_ui(self):
        # الرئيسية layout
        main_layout = QHBoxLayout(self)

        # --- Sidebar ---
        sidebar = QListWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #2c3e50; color: white; font-size: 16px;")
        sidebar.addItem(QListWidgetItem("🏠 Acceuil"))
        sidebar.addItem(QListWidgetItem("📦 Products"))
        sidebar.addItem(QListWidgetItem("🧾 Factures"))
        sidebar.addItem(QListWidgetItem("📊 Stock"))
        sidebar.setCurrentRow(1)  # default: products

        # --- Main Content Area ---
        self.stack = QStackedLayout()

        self.products_page = self.create_products_page()
        self.stack.addWidget(self.products_page)

        # Placeholder pages
        self.stack.addWidget(QLabel("🏠 مرحبًا بك في Acceuil"))
        self.stack.addWidget(QLabel("🧾 فاتوراتك هنا"))
        self.stack.addWidget(QLabel("📊 المخزون"))

        # Change page when clicked
        sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)

        main_layout.addWidget(sidebar)
        main_layout.addLayout(self.stack)

    def create_products_page(self):
        page = QWidget()
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.refresh_btn = QPushButton("🔄 تحديث المنتجات")
        self.add_btn = QPushButton("➕ إضافة منتج")
        self.delete_btn = QPushButton("🗑️ حذف المنتج")

        for btn in [self.refresh_btn, self.add_btn, self.delete_btn]:
            btn.setFixedHeight(40)
            btn.setStyleSheet("background-color: #3498db; color: white; font-size: 16px; border-radius: 5px;")

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.delete_btn)

        layout.addLayout(btn_layout)
        page.setLayout(layout)

        self.refresh_btn.clicked.connect(self.load_products)
        return page

    def load_products(self):
        try:
            response = requests.get(API_URL)
            response.raise_for_status()
            products = response.json()

            self.table.setRowCount(len(products))
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["الإسم", "الثمن", "الفئة", "رابط الصورة"])

            for row, p in enumerate(products):
                self.table.setItem(row, 0, QTableWidgetItem(p["name"]))
                self.table.setItem(row, 1, QTableWidgetItem(str(p["price"])))
                self.table.setItem(row, 2, QTableWidgetItem(p["category"]))
                self.table.setItem(row, 3, QTableWidgetItem(p["image"]))

        except Exception as e:
            print("❌ خطأ أثناء تحميل المنتجات:", e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdminPanel()
    window.show()
    sys.exit(app.exec_())
