from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

# -------------------
# Custom User
# -------------------
class User(AbstractUser):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
    ]

    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="other")  # NEW
    birthday = models.DateField(null=True, blank=True)
    salvation_date = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    user_type = models.IntegerField(choices=[(1, "Teacher"), (2, "Student")], default = 2)
    qr_value = models.CharField(max_length=100, unique=True, blank=True, null=True)
    qr_image = models.ImageField(upload_to="qr_codes/", null=True, blank=True)
    profile_pic = models.ImageField(upload_to="profiles/", null=True, blank=True)


    def save(self, *args, **kwargs):
        if not self.qr_value:
            self.qr_value = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


# -------------------
# Student Profile
# -------------------
class DimStudent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    level = models.IntegerField(default=1)
    streak = models.IntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)
    date_created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        if self.user.first_name or self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}".strip()
        return self.user.username


# -------------------
# Wallet + Transactions
# -------------------
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet({self.user.username}) - {self.balance}"


class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    amount = models.IntegerField()
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ("earn", "Earn"),
            ("spend", "Spend"),
            ("transfer", "Transfer"),
            ("refund", "Refund"),
            ("adjustment", "Adjustment"),
        ],
    )
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.transaction_type} {self.amount} ({self.wallet.user.username})"


# -------------------
# Store Models
# -------------------
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price_in_points = models.IntegerField()
    stock = models.IntegerField(default=0)
    image = models.ImageField(upload_to="products/", null=True, blank=True)

    def __str__(self):
        return self.name


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Cart({self.user.username})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    is_selected = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} ({self.cart.user.username})"


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("preparing", "Preparing"),
        ("delivering", "Delivering"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    points_spent = models.IntegerField()

    def __str__(self):
        return f"{self.product.name} x {self.quantity} ({self.order.user.username})"


# -------------------
# QR Scan + Notifications
# -------------------
class QRScanLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scanned_logs")  # the scanned person
    scanned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scanner_logs")  # teacher/admin
    points_given = models.IntegerField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.scanned_by.username} scanned {self.user.username} ({self.points_given} pts)"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Notification for {self.user.username}"
