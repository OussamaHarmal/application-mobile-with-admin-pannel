from django.db import models
from django.core.exceptions import ValidationError


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(default="", blank=True)  # ✅ مايبقاش يوقفك
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # ✅ default
    image = models.ImageField(upload_to='products/', blank=True, null=True)  # ✅ يقبل فارغ
    category = models.CharField(max_length=50, default="general")  # ✅ default

    stock = models.PositiveIntegerField(default=10)
    min_stock = models.PositiveIntegerField(default=5)

    def __str__(self):
        return self.name


class Order(models.Model):
    client_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # ✅ يقبل القديم

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('shipped', 'Shipped')
        ],
        default='pending'
    )

    def __str__(self):
        return f"Order {self.id} by {self.client_name}"

    @property
    def paid(self):
        return self.status == "paid"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)  # ✅ عندو default
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # ✅ default

    def save(self, *args, **kwargs):
        # التحقق من الستوك
        if self._state.adding:
            if self.product.stock < self.quantity:
                raise ValidationError("المخزون غير كافي لهذا المنتج")
            self.product.stock -= self.quantity
        else:
            old = OrderItem.objects.get(pk=self.pk)
            diff = self.quantity - old.quantity
            if diff > 0 and self.product.stock < diff:
                raise ValidationError("المخزون غير كافي للتعديل")
            self.product.stock -= diff

        self.product.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # إرجاع الكمية عند الحذف
        self.product.stock += self.quantity
        self.product.save()
        super().delete(*args, **kwargs)
