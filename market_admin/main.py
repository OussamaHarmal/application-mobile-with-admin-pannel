import sys
import requests
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from functools import partial
from PyQt6.QtCore import Qt

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QListWidget,
    QVBoxLayout, QHBoxLayout, QMessageBox, QLabel, QStackedLayout,
    QComboBox, QScrollArea, QGridLayout, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QDialog, QInputDialog, QFormLayout , QFileDialog, QTabWidget
)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt

from api_service import ApiService
from product_form import ProductForm


# -------------------- Helpers --------------------
def fmt_date(s):
    if not s:
        return ""
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        try:
            return s[:16]
        except Exception:
            return str(s)


def num_item(text):
    it = QTableWidgetItem(text)
    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return it


# -------------------- Invoice Details Dialog --------------------
class InvoiceDetailsDialog(QDialog):
    def __init__(self, parent, order: dict):
        super().__init__(parent)
        self.setWindowTitle(f"تفاصيل الفاتورة #{order.get('id','')}")
        self.setMinimumWidth(560)
        self.order = order

        layout = QVBoxLayout(self)

        # Header info
        info = QLabel(
            f"الزبون: {order.get('client_name','')}\n"
            f"التاريخ: {fmt_date(order.get('date') or order.get('created_at') or order.get('order_date'))}\n"
            f"الحالة: {'✅ مدفوعة' if order.get('paid', False) else '❌ غير مدفوعة'}"
        )
        info.setStyleSheet("font-weight:600;margin-bottom:6px;")
        layout.addWidget(info)

        # Items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(["المعرف", "المنتج", "الكمية", "السعر", "المجموع"])
        self._tune_table(self.items_table)
        layout.addWidget(self.items_table)

        items = order.get("items", []) or order.get("order_items", [])
        self.items_table.setRowCount(len(items))
        total_sum = 0.0
        for i, item in enumerate(items):
            pid = self._resolve_product_id(item)
            pname = self._resolve_product_name(item)
            quantity = int(item.get("quantity", item.get("qty", 0)) or 0)
            price = float(item.get("price", item.get("unit_price", 0)) or 0)
            line_total = price * quantity
            total_sum += line_total

            self.items_table.setItem(i, 0, QTableWidgetItem(str(pid) if pid else ""))
            self.items_table.setItem(i, 1, QTableWidgetItem(pname))
            self.items_table.setItem(i, 2, num_item(str(quantity)))
            self.items_table.setItem(i, 3, num_item(f"{price:.2f}"))
            self.items_table.setItem(i, 4, num_item(f"{line_total:.2f}"))

        # Footer total
        self.total_label = QLabel(f"المجموع: {order.get('total', total_sum)}Dh")
        self.total_label.setStyleSheet("margin-top:8px;font-size:16px;font-weight:bold;")
        layout.addWidget(self.total_label)

        # Actions
        btns = QHBoxLayout()
        self.mark_paid_btn = QPushButton("وضع كـ مدفوعة")
        self.mark_unpaid_btn = QPushButton("وضع كـ غير مدفوعة")
        self.print_btn = QPushButton("📥 تحميل الفاتورة (PDF)")
        self.close_btn = QPushButton("إغلاق")

        self.mark_paid_btn.clicked.connect(lambda: self._update_status(True))
        self.mark_unpaid_btn.clicked.connect(lambda: self._update_status(False))
        self.print_btn.clicked.connect(self._download_ticket)
        self.close_btn.clicked.connect(self.accept)

        btns.addWidget(self.mark_paid_btn)
        btns.addWidget(self.mark_unpaid_btn)
        btns.addStretch()
        btns.addWidget(self.print_btn)
        btns.addWidget(self.close_btn)
        layout.addLayout(btns)

    def _tune_table(self, table: QTableWidget):
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        f = QFont(); f.setBold(True)
        table.horizontalHeader().setFont(f)
        table.setAlternatingRowColors(True)

    def _resolve_product_id(self, item: dict):
        prod = item.get("product")
        if isinstance(prod, dict):
            return prod.get("id")
        if isinstance(prod, int):
            return prod
        return item.get("product_id")

    def _resolve_product_name(self, item: dict):
        name = item.get("product_name")
        if name:
            return name
        prod = item.get("product")
        try:
            if isinstance(prod, dict):
                if prod.get("name"):
                    return prod["name"]
                if prod.get("id"):
                    data = ApiService.get_product_by_id(prod["id"])  # requires backend endpoint
                    return data.get("name", "غير معروف")
            if isinstance(prod, int):
                data = ApiService.get_product_by_id(prod)
                return data.get("name", "غير معروف")
        except Exception:
            pass
        return "غير معروف"

    def _update_status(self, paid: bool):
        try:
            ApiService.update_order_status(self.order["id"], paid)  # requires backend endpoint
            self.order["paid"] = paid
            QMessageBox.information(self, "تم", "تم تحديث حالة الفاتورة")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر تحديث الحالة: {e}")

    def _download_ticket(self):
        try:
            AdminPanel.export_pdf(self.order, parent=self)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر توليد PDF: {e}")


# -------------------- Main Window --------------------
class AdminPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("لوحة التحكم - Admin Panel")
        self.setGeometry(100, 100, 1200, 720)

        self.setStyleSheet(
            """
            QWidget { background-color: #f4f5f7; font-family: 'Segoe UI', sans-serif; font-size: 14px; color: #2d3436; }
            QListWidget#sidebar { background-color: #2d3436; color: white; font-size: 16px; border: none; padding-top: 20px; }
            QListWidget#sidebar::item { padding: 14px 10px; margin: 4px 8px; border-radius: 10px; }
            QListWidget#sidebar::item:selected { background-color: #0984e3; color: white; }
            QPushButton { background-color: #0984e3; color: white; padding: 10px 14px; border: none; border-radius: 8px; font-size: 14px; }
            QPushButton:hover { background-color: #74b9ff; }
            QPushButton:pressed { background-color: #40739e; }
            QTableWidget { background: #ffffff; border-radius: 10px; gridline-color: #dfe6e9; }
            QHeaderView::section { background: #dfe6e9; padding: 8px; border: none; }
            """
        )

        main_widget = QWidget(); main_layout = QHBoxLayout(main_widget); self.setCentralWidget(main_widget)

        # Sidebar
        self.sidebar = QListWidget(objectName="sidebar")
        self.sidebar.setFixedWidth(220)
        self.sidebar.addItem("🏠 الرئيسية")
        self.sidebar.addItem("📦 المنتجات")
        self.sidebar.addItem("🧾 الفواتير")
        self.sidebar.addItem("📊 المخزون")
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self.change_page)

        # Pages stack
        self.stack = QStackedLayout()
        self.home_page = self.create_home_page()
        self.products_page = self.create_products_page()
        self.invoices_page = self.create_invoices_page()
        self.stock_page = self.create_stock_page()

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.products_page)
        self.stack.addWidget(self.invoices_page)
        self.stack.addWidget(self.stock_page)

        main_layout.addWidget(self.sidebar)
        main_layout.addLayout(self.stack)

        self.load_products()

    # ---------- Navigation ----------
    def change_page(self, index):
        self.stack.setCurrentIndex(index)
        if index == 2:
            self.load_invoices()
        elif index == 3:
            self.load_stock()

    # ---------- Pages ----------
    def create_home_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        title = QLabel("🏠 مرحبًا بك في لوحة التحكم"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin: 24px; color: #273c75;")
        layout.addWidget(title)
        return page

    def create_products_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        top_bar = QHBoxLayout(); add_btn = QPushButton("➕ إضافة منتج"); add_btn.clicked.connect(self.open_add_form)
        top_bar.addWidget(add_btn); top_bar.addStretch(); top_bar.addWidget(QLabel("الفئة:"))
        self.category_filter = QComboBox(); self.category_filter.addItems(["الكل", "الشاي", "السكر", "الزيت", "الدقيق", "أخرى"])
        self.category_filter.currentTextChanged.connect(self.load_products); top_bar.addWidget(self.category_filter)
        layout.addLayout(top_bar)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True)
        self.products_container = QWidget(); self.products_grid = QGridLayout(self.products_container)
        self.products_grid.setContentsMargins(6, 6, 6, 6); self.products_grid.setHorizontalSpacing(10); self.products_grid.setVerticalSpacing(10)
        scroll_area.setWidget(self.products_container); layout.addWidget(scroll_area)
        return page

    def create_invoices_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        title = QLabel("🧾 قائمة الفواتير"); title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)

        # Filters bar
        filters = QHBoxLayout()
        filters.addWidget(QLabel("بحث:"))
        self.invoice_search = QLineEdit(); self.invoice_search.setPlaceholderText("اسم الزبون / رقم الفاتورة")
        self.invoice_search.textChanged.connect(self._apply_invoice_filters)
        filters.addWidget(self.invoice_search)

        filters.addSpacing(12)
        filters.addWidget(QLabel("الحالة:"))
        self.status_filter = QComboBox(); self.status_filter.addItems(["الكل", "مدفوعة", "غير مدفوعة"])  # filter paid/unpaid
        self.status_filter.currentTextChanged.connect(self._apply_invoice_filters)
        filters.addWidget(self.status_filter)

        refresh_btn = QPushButton("🔄 تحديث"); refresh_btn.clicked.connect(self.load_invoices); filters.addWidget(refresh_btn)
        filters.addStretch()
        layout.addLayout(filters)

        # Invoices table (no details inline)
        self.invoices_table = QTableWidget(); self.invoices_table.setColumnCount(5)
        self.invoices_table.setHorizontalHeaderLabels(["رقم", "المجموع", "التاريخ", "الزبون", "الحالة"])
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.invoices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.invoices_table.cellDoubleClicked.connect(self.open_invoice_dialog)  # open details only on double click
        self.tune_table(self.invoices_table); layout.addWidget(self.invoices_table)

        return page

    def create_stock_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        title = QLabel("📊 إدارة المخزون"); title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)

        # Controls
        bar = QHBoxLayout()
        bar.addWidget(QLabel("بحث:"))
        self.stock_search = QLineEdit(); self.stock_search.setPlaceholderText("اسم المنتج / الفئة / الكود")
        self.stock_search.textChanged.connect(self._apply_stock_filters); bar.addWidget(self.stock_search)

        bar.addSpacing(12); bar.addWidget(QLabel("عرض:"))
        self.stock_filter = QComboBox(); self.stock_filter.addItems(["الكل", "الكمية منخفضة", "غير متوفر"])
        self.stock_filter.currentTextChanged.connect(self._apply_stock_filters); bar.addWidget(self.stock_filter)

        refresh = QPushButton("🔄 تحديث"); refresh.clicked.connect(self.load_stock); bar.addWidget(refresh)
        bar.addStretch()

        inc_btn = QPushButton("➕ زيادة الكمية"); inc_btn.clicked.connect(self.increase_stock)
        dec_btn = QPushButton("➖ تقليل الكمية"); dec_btn.clicked.connect(self.decrease_stock)
        set_min_btn = QPushButton("⚙️ حد أدنى للتنبيه"); set_min_btn.clicked.connect(self.set_min_stock)
        bar.addWidget(inc_btn); bar.addWidget(dec_btn); bar.addWidget(set_min_btn)
        layout.addLayout(bar)

        # Stock table
        self.stock_table = QTableWidget(); self.stock_table.setColumnCount(7)
        self.stock_table.setHorizontalHeaderLabels(["ID", "المنتج", "الفئة", "السعر", "الكمية", "الحد الأدنى", "آخر تحديث"])
        self.tune_table(self.stock_table); layout.addWidget(self.stock_table)
        return page

    # ---------- Styling helpers ----------
    def tune_table(self, table: QTableWidget):
        header = table.horizontalHeader(); header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        font = QFont(); font.setBold(True)
        table.horizontalHeader().setFont(font)
        table.setAlternatingRowColors(True)

    # ---------- Products ----------
    def load_products(self):
        try:
            products = ApiService.get_products()
            selected_category = self.category_filter.currentText() if hasattr(self, "category_filter") else "الكل"
            if selected_category != "الكل":
                products = [p for p in products if p.get("category") == selected_category]

            for i in reversed(range(self.products_grid.count())):
                w = self.products_grid.itemAt(i).widget()
                if w: w.setParent(None)

            row, col = 0, 0
            for p in products:
                card = self.create_product_card(p)
                self.products_grid.addWidget(card, row, col)
                col += 1
                if col >= 3:
                    col, row = 0, row + 1
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تحميل المنتجات: {e}")

    def open_add_form(self):
        form = ProductForm(self)
        if form.exec(): self.load_products()

    def delete_product_by_id(self, product_id):
        confirm = QMessageBox.question(self, "تأكيد", "هل أنت متأكد من حذف المنتج؟")
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                ApiService.delete_product(product_id); self.load_products()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل الحذف: {e}")

    def modify_product(self, product):
        form = ProductForm(self, product)
        if form.exec(): self.load_products()

    def create_product_card(self, product):
        frame = QFrame(); frame.setFrameShape(QFrame.Shape.StyledPanel); frame.setStyleSheet("background:#fff;border-radius:14px;")
        layout = QVBoxLayout(frame); layout.setContentsMargins(12, 12, 12, 12)
        image_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter); image_label.setMinimumHeight(130)
        img_url = product.get("image")
        if img_url:
            try:
                resp = requests.get(img_url, timeout=6)
                if resp.status_code == 200:
                    pixmap = QPixmap(); pixmap.loadFromData(BytesIO(resp.content).read())
                    image_label.setPixmap(pixmap.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    image_label.setText("صورة غير متوفرة")
            except Exception:
                image_label.setText("خطأ في تحميل الصورة")
        else:
            image_label.setText("لا توجد صورة")

        name_label = QLabel(product.get("name", "بدون اسم")); name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-weight:600; margin-top:6px;")

        btns = QHBoxLayout(); modify_btn = QPushButton("✏️ تعديل"); modify_btn.clicked.connect(lambda: self.modify_product(product))
        delete_btn = QPushButton("🗑️ حذف"); delete_btn.clicked.connect(lambda: self.delete_product_by_id(product.get("id")))
        btns.addWidget(modify_btn); btns.addWidget(delete_btn)

        layout.addWidget(image_label); layout.addWidget(name_label); layout.addLayout(btns)
        return frame
    

    # ---------- Invoices ----------
    def load_invoices(self):
        try:
            invoices = ApiService.get_orders()
            self._all_invoices = invoices
            self._apply_invoice_filters()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تحميل الفواتير: {e}")


    def _apply_invoice_filters(self):
        if not hasattr(self, "_all_invoices"):
            return

        text = (self.invoice_search.text() or "").strip().lower() if hasattr(self, "invoice_search") else ""
        status_filter = getattr(self, "status_filter", None)
        status = status_filter.currentText() if status_filter else "الكل"

        filtered = []
        for inv in self._all_invoices:
            order_id = str(inv.get("id", ""))
            client_name = (inv.get("client_name") or inv.get("customer_name") or inv.get("name") or "").lower()
            status_value = str(inv.get("status", "")).lower()
            paid = status_value == "paid"

            if text and (text not in order_id.lower() and text not in client_name):
                continue
            if status == "مدفوعة" and not paid:
                continue
            if status == "غير مدفوعة" and paid:
                continue

            filtered.append(inv)

        self._current_invoices = filtered

        if hasattr(self, "invoices_table"):
            self.invoices_table.setColumnCount(8)
            self.invoices_table.setHorizontalHeaderLabels([
                "رقم", "المجموع", "التاريخ", "الزبون", "الحالة", "تغيير الحالة", "تحميل PDF", "حذف"
            ])
            self.invoices_table.setRowCount(len(filtered))

            self.invoices_table.verticalHeader().setDefaultSectionSize(50)

            for row, inv in enumerate(filtered):
                order_id = str(inv.get("id", ""))
                total = str(inv.get("total", inv.get("total_price", "")))
                date_raw = inv.get("date") or inv.get("created_at") or inv.get("order_date") or ""
                date = fmt_date(date_raw) if callable(fmt_date) else str(date_raw)
                client = inv.get("client_name") or inv.get("customer_name") or inv.get("name") or ""
                status_value = str(inv.get("status", "")).lower()
                paid_status = "✅ مدفوعة" if status_value == "paid" else "❌ غير مدفوعة"

                self.invoices_table.setItem(row, 0, QTableWidgetItem(order_id))
                self.invoices_table.setItem(row, 1, QTableWidgetItem(total))
                self.invoices_table.setItem(row, 2, QTableWidgetItem(date))
                self.invoices_table.setItem(row, 3, QTableWidgetItem(client))
                self.invoices_table.setItem(row, 4, QTableWidgetItem(paid_status))

                # زر تغيير الحالة
                btn_status = QPushButton("تغيير الحالة")
                btn_status.clicked.connect(partial(self.change_invoice_status, order_id, status_value))
                self.invoices_table.setCellWidget(row, 5, btn_status)

                # زر تحميل PDF
                btn_pdf = QPushButton("📄 تحميل PDF")
                btn_pdf.clicked.connect(partial(self.download_invoice_pdf, inv))
                self.invoices_table.setCellWidget(row, 6, btn_pdf)

                # زر حذف الفاتورة
                btn_delete = QPushButton("🗑 حذف")
                btn_delete.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 5px;")
                btn_delete.clicked.connect(partial(self.delete_invoice, order_id))
                self.invoices_table.setCellWidget(row, 7, btn_delete)

            try:
                self.invoices_table.cellDoubleClicked.disconnect()
            except:
                pass
            self.invoices_table.cellDoubleClicked.connect(self.open_invoice_dialog)
            

    def change_invoice_status(self, order_id, current_status):
        status_str = str(current_status).lower().strip()

        if status_str in ["paid", "مدفوعة", "✅ مدفوعة"]:
            new_status = "pending"
        else:
            new_status = "paid"

        success = ApiService.update_order_status(order_id, new_status)

        if success:
            QMessageBox.information(self, "نجاح", f"تم تغيير الحالة إلى {new_status.upper()}")
            self.load_invoices()
        else:
            QMessageBox.critical(self, "خطأ", "فشل تحديث حالة الفاتورة")




    def delete_invoice(self, *args, **kwargs):
        selected = self.invoices_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "تحذير", "المرجو اختيار فاتورة للحذف")
            return

        invoice_id = self.invoices_table.item(selected, 0).text()
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            "هل أنت متأكد أنك تريد حذف هذه الفاتورة؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = ApiService.delete_order(invoice_id)
            if success:
                QMessageBox.information(self, "نجاح", "تم حذف الفاتورة بنجاح")
                self.load_invoices()
            else:
                QMessageBox.critical(self, "خطأ", "فشل حذف الفاتورة")


    def download_invoice_pdf(self, invoice):
        try:
            invoice_id = str(invoice.get("id", ""))

            if not invoice_id:
                QMessageBox.warning(self, "تحذير", "معرف الفاتورة غير صالح")
                return

            # نطلب من API باش يرجع PDF
            pdf_data = ApiService.download_invoice_pdf(invoice_id)

            if pdf_data:
                # نخلي المستخدم يختار مكان الحفظ
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "حفظ الفاتورة PDF",
                    f"invoice_{invoice_id}.pdf",
                    "PDF Files (*.pdf)"
                )
                if file_path:
                    with open(file_path, "wb") as f:
                        f.write(pdf_data)
                    QMessageBox.information(self, "نجاح", "تم تحميل الفاتورة بنجاح!")
            else:
                QMessageBox.critical(self, "خطأ", "الخادم لم يرجع أي ملف PDF")

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تحميل الفاتورة: {e}")



    def open_invoice_dialog(self, row, column):
        try:
            invoice_summary = self._current_invoices[row]
            order_id = invoice_summary.get("id", "")

            # نجيب تفاصيل الفاتورة من API
            invoice = ApiService.get_order_by_id(order_id)
            items = invoice.get("items", [])
            print("DEBUG items from API:", items)

            # نافذة جديدة
            dialog = QDialog(self)
            dialog.setWindowTitle(f"تفاصيل الفاتورة #{order_id}")
            dialog.resize(750, 500)

            main_layout = QVBoxLayout(dialog)

            # ---- جدول العناصر فقط ----
            if items and isinstance(items, list):
                table = QTableWidget()
                table.setColumnCount(5)  # زدنا عمود للوصف
                table.setHorizontalHeaderLabels(["المنتج", "الوصف", "الكمية", "السعر", "المجموع"])
                table.setRowCount(len(items))

                for row_idx, item in enumerate(items):
                    name = item.get("product_name") or item.get("name") or f"منتج #{item.get('product', '')}"
                    description = item.get("description", "بدون وصف")  # الوصف من API أو افتراضي
                    quantity = int(item.get("quantity", 1))
                    price = float(item.get("price", 0))
                    total_price = quantity * price

                    table.setItem(row_idx, 0, QTableWidgetItem(str(name)))
                    table.setItem(row_idx, 1, QTableWidgetItem(str(description)))
                    table.setItem(row_idx, 2, QTableWidgetItem(str(quantity)))
                    table.setItem(row_idx, 3, QTableWidgetItem(f"{price:.2f}"))
                    table.setItem(row_idx, 4, QTableWidgetItem(f"{total_price:.2f}"))

                table.resizeColumnsToContents()
                table.horizontalHeader().setStretchLastSection(True)
                main_layout.addWidget(table)
            else:
                main_layout.addWidget(QLabel("لا توجد عناصر مرتبطة بهذه الفاتورة"))

            # زر إغلاق
            btn_close = QPushButton("إغلاق")
            btn_close.setStyleSheet(
                "background-color: #d9534f; color: white; padding: 6px 18px; border-radius: 8px;"
            )
            btn_close.clicked.connect(dialog.close)
            main_layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

            dialog.exec()

        except Exception as e:
            QMessageBox.c



            
            
    # ---------- Stock ----------
    def load_stock(self):
        try:
            # Prefer a dedicated stock endpoint; fallback to products list
            try:
                stock = ApiService.get_stock()  # optional endpoint on your API
            except Exception:
                stock = ApiService.get_products()
            self._all_stock = stock
            self._apply_stock_filters()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تحميل المخزون: {e}")

    def _apply_stock_filters(self):
        if not hasattr(self, "_all_stock"): return
        text = (self.stock_search.text() or "").strip().lower()
        mode = self.stock_filter.currentText() if hasattr(self, "stock_filter") else "الكل"

        rows = []
        for p in self._all_stock:
            pid = p.get("id"); name = p.get("name", ""); cat = p.get("category", "")
            price = p.get("price", p.get("unit_price", 0))
            qty = p.get("stock", p.get("quantity", 0))
            min_stock = p.get("min_stock", p.get("min", 0))
            updated = fmt_date(p.get("updated_at") or p.get("modified") or p.get("created_at"))

            # search filter
            hay = f"{pid} {name} {cat}".lower()
            if text and text not in hay:
                continue
            # status filter
            if mode == "الكمية منخفضة" and not (isinstance(min_stock, (int,float)) and qty <= min_stock):
                continue
            if mode == "غير متوفر" and not (qty == 0):
                continue
            rows.append((pid, name, cat, price, qty, min_stock, updated))

        self.stock_table.setRowCount(len(rows))
        for r, (pid, name, cat, price, qty, min_stock, updated) in enumerate(rows):
            self.stock_table.setItem(r, 0, num_item(str(pid)))
            self.stock_table.setItem(r, 1, QTableWidgetItem(name))
            self.stock_table.setItem(r, 2, QTableWidgetItem(cat))
            self.stock_table.setItem(r, 3, num_item(f"{float(price):.2f}"))
            self.stock_table.setItem(r, 4, num_item(str(int(qty) if isinstance(qty, (int,float)) else qty)))
            self.stock_table.setItem(r, 5, num_item(str(int(min_stock) if isinstance(min_stock, (int,float)) else min_stock)))
            self.stock_table.setItem(r, 6, QTableWidgetItem(updated))

        # highlight low stock
        for r in range(self.stock_table.rowCount()):
            try:
                qty = int(self.stock_table.item(r, 4).text())
                min_s = int(self.stock_table.item(r, 5).text())
                if qty <= min_s:
                    for c in range(self.stock_table.columnCount()):
                        self.stock_table.item(r, c).setBackground(Qt.GlobalColor.yellow)
            except Exception:
                pass

    def _selected_stock_product_id(self):
        row = self.stock_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "حدد منتجًا أولاً من جدول المخزون")
            return None
        return int(self.stock_table.item(row, 0).text())

    def increase_stock(self):
        pid = self._selected_stock_product_id()
        if pid is None: return
        val, ok = QInputDialog.getInt(self, "زيادة الكمية", "بكم تريد الزيادة؟", 1, 1, 100000, 1)
        if not ok: return
        try:
            ApiService.update_stock(pid, "+", val)  # requires backend endpoint
            QMessageBox.information(self, "تم", "تم تحديث المخزون")
            self.load_stock()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر التحديث: {e}")

    def decrease_stock(self):
        pid = self._selected_stock_product_id()
        if pid is None: return
        val, ok = QInputDialog.getInt(self, "تقليل الكمية", "بكم تريد التقليل؟", 1, 1, 100000, 1)
        if not ok: return
        try:
            ApiService.update_stock(pid, "-", val)  # requires backend endpoint
            QMessageBox.information(self, "تم", "تم تحديث المخزون")
            self.load_stock()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر التحديث: {e}")

    def set_min_stock(self):
        pid = self._selected_stock_product_id()
        if pid is None: return
        val, ok = QInputDialog.getInt(self, "حد أدنى", "الكمية الدنيا للتنبيه:", 5, 0, 100000, 1)
        if not ok: return
        try:
            ApiService.set_min_stock(pid, val)  # requires backend endpoint
            QMessageBox.information(self, "تم", "تم حفظ الحد الأدنى")
            self.load_stock()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر الحفظ: {e}")


# -------------------- App Entry --------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AdminPanel()
    window.show()
    sys.exit(app.exec())
