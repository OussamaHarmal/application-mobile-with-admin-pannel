import requests

class ApiService:
    BASE_URL = 'http://127.0.0.1:8000/api'
    TIMEOUT = 10  # ثواني المهلة القصوى

    # -------------------- المنتجات --------------------

    @staticmethod
    def get_products():
        """جلب جميع المنتجات"""
        try:
            response = requests.get(f"{ApiService.BASE_URL}/products/", timeout=ApiService.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"فشل تحميل المنتجات: {e}")

    @staticmethod
    def get_product_by_id(product_id: int):
        """جلب منتج معين بالمعرف"""
        try:
            response = requests.get(f"{ApiService.BASE_URL}/products/{product_id}/", timeout=ApiService.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"فشل جلب المنتج بالمعرف: {e}")

    @staticmethod
    def add_product(data: dict, image_path: str = None):
        """إضافة منتج جديد مع الصورة"""
        try:
            files = None
            if image_path:
                files = {"image": open(image_path, "rb")}
            payload = {
                "name": data["name"],
                "price": data["price"],
                "category": data["category"],
                "description": data.get("description", ""),
                "stock": data.get("stock", 0),
                "min_stock": data.get("min_stock", 0),
            }
            response = requests.post(
                f"{ApiService.BASE_URL}/products/",
                data=payload,
                files=files,
                timeout=ApiService.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"فشل إضافة المنتج: {e}")
        finally:
            if files:
                files["image"].close()

    @staticmethod
    def update_product(product_id: int, data: dict):
        """تحديث بيانات المنتج"""
        try:
            response = requests.patch(
                f"{ApiService.BASE_URL}/products/{product_id}/",
                json=data,
                timeout=ApiService.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"فشل تحديث المنتج: {e}")

    @staticmethod
    def delete_product(product_id: int):
        """حذف المنتج"""
        try:
            response = requests.delete(
                f"{ApiService.BASE_URL}/products/{product_id}/",
                timeout=ApiService.TIMEOUT,
            )
            response.raise_for_status()
            return response.status_code == 204
        except Exception as e:
            raise Exception(f"فشل حذف المنتج: {e}")

    # -------------------- الطلبات --------------------

    @staticmethod
    def get_orders():
        """جلب جميع الطلبات/الفواتير"""
        try:
            response = requests.get(f"{ApiService.BASE_URL}/orders/", timeout=ApiService.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"فشل تحميل الفواتير: {e}")

    @staticmethod
    def update_order_status(order_id: int, new_status: str):
        try:
            response = requests.patch(
                f"{ApiService.BASE_URL}/orders/{order_id}/",
                json={"status": new_status},   # 👈 هنا نص (paid / pending)
                timeout=ApiService.TIMEOUT,
            )
            response.raise_for_status()
            print("DEBUG RESPONSE:", response.json())  # 👈 باش تشوف واش تبدلات
            return True
        except Exception as e:
            print("Error update_order_status:", e)
            return False


    # -------------------- المخزون --------------------

    @staticmethod
    def get_stock():
        """جلب المخزون (يعتمد على المنتجات)"""
        return ApiService.get_products()

    @staticmethod
    def update_stock(product_id: int, operation: str, value: int):
        """
        تحديث كمية المخزون لمنتج معين
        operation: '+' أو '-'
        value: الكمية المراد تعديلها
        """
        try:
            product = ApiService.get_product_by_id(product_id)
            current_qty = product.get("stock", 0)

            if operation == "+":
                new_qty = current_qty + value
            elif operation == "-":
                new_qty = max(0, current_qty - value)
            else:
                raise ValueError("عملية غير صالحة. استعمل '+' أو '-'.")

            payload = {"stock": new_qty}
            response = requests.patch(
                f"{ApiService.BASE_URL}/products/{product_id}/",
                json=payload,
                timeout=ApiService.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"فشل تحديث المخزون: {e}")

    @staticmethod
    def set_min_stock(product_id: int, value: int):
        """تحديد الحد الأدنى للمخزون"""
        try:
            payload = {"min_stock": value}
            response = requests.patch(
                f"{ApiService.BASE_URL}/products/{product_id}/",
                json=payload,
                timeout=ApiService.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"فشل تحديد الحد الأدنى للمخزون: {e}")
        
    @staticmethod
    def delete_order(order_id):
        url = f"{ApiService.BASE_URL}/orders/{order_id}/"  # 👈 خاص / فالآخر
        try:
            r = requests.delete(url)
            print("DELETE Response:", r.status_code, r.text)  # Debug
            return r.status_code == 204  # Django REST كيرجع 204 No Content
        except Exception as e:
            print("Error deleting order:", e)
            return False


    @staticmethod
    def download_invoice_pdf(invoice_id):
        try:
            url = f"{ApiService.BASE_URL}/invoices/{invoice_id}/download"  # غيّر الرابط حسب API ديالك
            response = requests.get(url)
            if response.status_code == 200:
                return response.content  # Bytes ديال PDF
            return None
        except Exception as e:
            print(f"Error downloading PDF: {e}")
            return None


    @staticmethod
    def get_order_by_id(order_id: int):
        try:
            response = requests.get(f"{ApiService.BASE_URL}/orders/{order_id}/", timeout=ApiService.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"فشل جلب تفاصيل الطلب: {e}")

    @staticmethod
    def download_invoice_pdf(order_id: int):
        url = f"{ApiService.BASE_URL}/orders/{order_id}/pdf/"
        response = requests.get(url)
        if response.status_code == 200 and response.headers.get("Content-Type") == "application/pdf":
            return response.content
        return None
