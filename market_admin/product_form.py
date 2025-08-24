from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QTextEdit,
    QPushButton, QFormLayout, QMessageBox, QFileDialog, QComboBox
)
from api_service import ApiService

class ProductForm(QDialog):
    def __init__(self, parent=None, product=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة منتج" if not product else "تعديل منتج")
        self.product = product

        self.name_input = QLineEdit()
        self.price_input = QLineEdit()
        self.description_input = QTextEdit()
        self.category_input = QComboBox()
        self.image_button = QPushButton("اختيار صورة")
        self.image_label = QLabel("لم يتم اختيار صورة")
        self.save_button = QPushButton("حفظ")

        # dummy categories (Remplace with real API call if needed)
        self.categories = ["الشاي", "سكر", "دقيق", "زيت", "أخرى"]
        self.category_input.addItems(self.categories)

        layout = QFormLayout()
        layout.addRow("اسم المنتج:", self.name_input)
        layout.addRow("السعر:", self.price_input)
        layout.addRow("الوصف:", self.description_input)
        layout.addRow("الفئة:", self.category_input)
        layout.addRow("الصورة:", self.image_button)
        layout.addRow("", self.image_label)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

        self.image_path = None

        if product:
            self.name_input.setText(product['name'])
            self.price_input.setText(str(product['price']))
            self.description_input.setPlainText(product['description'])
            self.category_input.setCurrentText(product.get('category', 'أخرى'))
            self.image_label.setText("الصورة الحالية محفوظة")

        self.image_button.clicked.connect(self.select_image)
        self.save_button.clicked.connect(self.save_product)

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "اختيار صورة", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.image_path = path
            self.image_label.setText(path.split("/")[-1])

    def save_product(self):
        data = {
            'name': self.name_input.text(),
            'price': self.price_input.text(),
            'description': self.description_input.toPlainText(),
            'category': self.category_input.currentText()
        }

        try:
            if self.product:
                ApiService.update_product(self.product['id'], data, self.image_path)
            else:
                ApiService.add_product(data, self.image_path)

            QMessageBox.information(self, "تم", "تم الحفظ بنجاح")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الحفظ: {str(e)}")
