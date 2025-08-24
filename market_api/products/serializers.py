from rest_framework import serializers
from .models import Product, Order, OrderItem


# ==========================
# Product Serializer
# ==========================
class ProductSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price',
            'category', 'image', 'image_url',
            'stock', 'min_stock'
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


# ==========================
# OrderItem Serializer
# ==========================
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price']
        read_only_fields = ['price']   # الكلاينت ميرسلوش


# ==========================
# Order Serializer
# ==========================
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, required=True)


    class Meta:
        model = Order
        fields = [
            'id', 'client_name', 'phone', 'email', 'city', 'address',
            'total', 'status', 'created_at', 'items'
        ]
        read_only_fields = ['total', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)

        total = 0
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']

            if product.stock < quantity:
                raise serializers.ValidationError(
                    f"❌ الكمية غير متوفرة للمنتج: {product.name}"
                )

            # إنشاء OrderItem
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=product.price  # unit price
            )

            # حساب المجموع
            total += product.price * quantity

            # تحديث المخزون
            product.stock -= quantity
            product.save()

        order.total = total
        order.save()
        return order

    def update(self, instance, validated_data):
        # إذا كان غير status اللي جاي فـ PATCH
        if list(validated_data.keys()) == ["status"]:
            instance.status = validated_data["status"]
            instance.save()
            return instance

        # استرجاع المخزون القديم
        for old_item in instance.items.all():
            old_item.product.stock += old_item.quantity
            old_item.product.save()

        instance.items.all().delete()

        # تحديث باقي المعلومات
        instance.status = validated_data.get('status', instance.status)
        instance.client_name = validated_data.get('client_name', instance.client_name)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.email = validated_data.get('email', instance.email)
        instance.city = validated_data.get('city', instance.city)
        instance.address = validated_data.get('address', instance.address)
        instance.save()

        # إعادة بناء items إذا تبعثو
        items_data = validated_data.pop('items', [])
        total = 0
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']

            if product.stock < quantity:
                raise serializers.ValidationError(
                    f"❌ الكمية غير متوفرة للمنتج: {product.name}"
                )

            OrderItem.objects.create(
                order=instance,
                product=product,
                quantity=quantity,
                price=product.price
            )

            total += product.price * quantity
            product.stock -= quantity
            product.save()

        instance.total = total
        instance.save()
        return instance
