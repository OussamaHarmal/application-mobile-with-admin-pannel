from rest_framework import viewsets
from rest_framework.decorators import action
from django.http import HttpResponse
from .models import Product, Order
from .serializers import ProductSerializer, OrderSerializer

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

import arabic_reshaper
from bidi.algorithm import get_display

# تسجيل الخط العربي
pdfmetrics.registerFont(TTFont('Arabic', r"C:\Users\dell\Desktop\projet complet\market_admin\Khalid Art bold Regular.ttf"))

def rtl(text):
    reshaped = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped)
    return bidi_text

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        order = self.get_object()

        buffer = BytesIO()
        width, height = 80 * mm, 200 * mm
        p = canvas.Canvas(buffer, pagesize=(width, height))

        y = height - 10 * mm
        x_margin = 5 * mm

        # Header
        p.setFont("Arabic", 12)
        p.drawCentredString(width / 2, y, rtl("متجر آتاي"))
        y -= 5
        p.setStrokeColor(colors.black)
        p.line(x_margin, y, width - x_margin, y)
        y -= 15

        # Infos client
        p.setFont("Arabic", 9)
        p.drawRightString(width - x_margin, y, rtl(f"الطلب: #{order.id:04d}"))
        y -= 12
        p.drawRightString(width - x_margin, y, rtl(f"الاسم: {order.client_name or '---'}"))
        y -= 12
        p.drawRightString(width - x_margin, y, rtl(f"الهاتف: {order.phone or '---'}"))
        y -= 12
        p.drawRightString(width - x_margin, y, rtl(f"المدينة: {order.city or '---'}"))
        y -= 16

        # Produits
        p.setFont("Arabic", 9)
        p.drawRightString(width - x_margin, y, rtl("المشتريات:"))
        y -= 10
        p.line(x_margin, y, width - x_margin, y)
        y -= 12

        for idx, item in enumerate(order.items.all(), start=1):
            total_item = float(item.price) * int(item.quantity)
            line = f"{idx}. {item.product.name} × {item.quantity} = {total_item:.2f} درهم"
            p.drawRightString(width - x_margin, y, rtl(line))
            y -= 12

            if y < 20 * mm:
                p.showPage()
                p.setFont("Arabic", 9)
                y = height - 20 * mm

        # Ligne avant total
        y -= 5
        p.line(x_margin, y, width - x_margin, y)
        y -= 12

        # Total
        p.setFont("Arabic", 10)
        p.drawRightString(width - x_margin, y, rtl(f"المجموع: {order.total} درهم"))
        y -= 16

        # Date et heure
        p.setFont("Arabic", 9)
        p.drawRightString(width - x_margin, y, rtl(f"التاريخ: {order.created_at.strftime('%Y-%m-%d')}"))
        y -= 12
        p.drawRightString(width - x_margin, y, rtl(f"الساعة: {order.created_at.strftime('%H:%M')}"))
        y -= 16

        # Footer
        p.line(x_margin, y, width - x_margin, y)
        y -= 12
        p.setFont("Arabic", 9)
        p.drawCentredString(width / 2, y, rtl("شكرا لاختياركم متجر آتاي!"))
        y -= 12
        p.drawCentredString(width / 2, y, rtl("الذوق الأصيل… من الطبيعة إلى بابكم"))

        p.showPage()
        p.save()

        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf, content_type="application/pdf")
        response['Content-Disposition'] = f'attachment; filename=\"invoice_{order.id}.pdf\"'
        return response
