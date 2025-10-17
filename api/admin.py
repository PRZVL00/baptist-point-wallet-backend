from django.contrib import admin
from .models import (
    User, DimStudent, Wallet, WalletTransaction,
    Product, Cart, CartItem, Order, OrderItem,
    QRScanLog, Notification
)

admin.site.register(User)
admin.site.register(DimStudent)
admin.site.register(Wallet)
admin.site.register(WalletTransaction)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(QRScanLog)
admin.site.register(Notification)