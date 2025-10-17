from rest_framework import serializers
from .models import *
from rest_framework import serializers
from .models import DimStudent

from rest_framework import serializers
from .models import User  # your custom User model
from django.contrib.auth.hashers import make_password
from .models import DimStudent, Wallet
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import DimStudent, Wallet

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from io import BytesIO
from django.core.files import File
import random
import string


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'user_type', 'profile_pic']

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'last_updated']

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price_in_points', 'stock', 'image']

#-------------------------------------------------------------------------------------------#
class WalletTransactionSerializer(serializers.ModelSerializer):
    icon = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()

    class Meta:
        model = WalletTransaction
        fields = ["id", "transaction_type", "amount", "description", "icon", "time", "color"]

    def get_icon(self, obj):
        mapping = {
            "earn": "🌟",
            "spend": "💸",
            "transfer": "🔄",
            "refund": "↩️",
            "adjustment": "⚖️",
        }
        return mapping.get(obj.transaction_type, "💰")

    def get_color(self, obj):
        return "text-green-500" if obj.transaction_type == "earn" else "text-red-500"

    def get_time(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")

#-------------------------------------------------------------------------------------------#
User = get_user_model()

class StudentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    firstName = serializers.CharField(write_only=True)
    lastName = serializers.CharField(write_only=True)
    phoneNumber = serializers.CharField(write_only=True, required=False)
    birthday = serializers.DateField(write_only=True, required=False)
    salvationDate = serializers.DateField(write_only=True, required=False)
    
    balance = serializers.IntegerField(source="user.wallet.balance", read_only=True)
    status = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    level = serializers.IntegerField(read_only=True)
    streak = serializers.IntegerField(read_only=True)
    last_activity = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    gender = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = DimStudent
        fields = [
            "id", "name", "username", "password", "email", "balance", "level",
            "streak", "last_activity", "status", "avatar", "gender",
            "firstName", "lastName", "phoneNumber", "birthday", "salvationDate"
        ]

    def create(self, validated_data):
        username = validated_data.pop("username")
        password = validated_data.pop("password")
        email = validated_data.pop("email", "")
        first_name = validated_data.pop("firstName", "")
        last_name = validated_data.pop("lastName", "")
        phone_number = validated_data.pop("phoneNumber", "")
        birthday = validated_data.pop("birthday", None)
        salvation_date = validated_data.pop("salvationDate", None)
        gender = validated_data.pop("gender", None)

        # 1️⃣ Generate random QR value
        qr_value = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

        # 2️⃣ Create the User
        user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            birthday=birthday,
            salvation_date=salvation_date,
            gender=gender,
            qr_value=qr_value,
        )
        user.set_password(password)

        # 3️⃣ Create the custom QR image
        qr_img = generate_qr_image(qr_value)
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        filename = f"{username}_qr.png"
        user.qr_image.save(filename, File(buffer), save=False)

        # 4️⃣ Save user
        user.save()

        # 5️⃣ Create Wallet and Student profile
        Wallet.objects.create(user=user, balance=0)
        student = DimStudent.objects.create(user=user, **validated_data)

        return student



    def get_status(self, obj):
        return "active" if obj.user.is_active else "inactive"

    def get_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    def get_last_activity(self, obj):
        if obj.last_activity:
            return obj.last_activity.strftime("%Y-%m-%d %H:%M:%S")
        elif obj.user.last_login:
            return obj.user.last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif hasattr(obj.user, "wallet") and getattr(obj.user.wallet, "last_updated", None):
            return obj.user.wallet.last_updated.strftime("%Y-%m-%d %H:%M:%S")
        return "N/A"

    def get_avatar(self, obj):
        if obj.user.gender == "male":
            return "👦"
        elif obj.user.gender == "female":
            return "👧"
        return "⭐"

# Add these new serializers to your existing serializers.py

class QRStudentSerializer(serializers.ModelSerializer):
    """Serializer for QR scan results - read-only student info"""
    name = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    streak = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'name', 'first_name', 'last_name', 
            'email', 'gender', 'balance', 'avatar', 'status', 
            'level', 'streak', 'qr_value', 'profile_pic'
        ]
        read_only_fields = fields

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_balance(self, obj):
        try:
            return obj.wallet.balance
        except Wallet.DoesNotExist:
            return 0

    def get_avatar(self, obj):
        if obj.gender == "male":
            return "👦"
        elif obj.gender == "female":
            return "👧"
        return "⭐"

    def get_status(self, obj):
        return "active" if obj.is_active else "inactive"

    def get_level(self, obj):
        try:
            return obj.student_profile.level
        except DimStudent.DoesNotExist:
            return 1

    def get_streak(self, obj):
        try:
            return obj.student_profile.streak
        except DimStudent.DoesNotExist:
            return 0


class AwardPointsSerializer(serializers.Serializer):
    """Serializer for awarding points - validates input"""
    student_id = serializers.IntegerField()
    points = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=500)

    def validate_points(self, value):
        if value <= 0:
            raise serializers.ValidationError("Points must be greater than 0")
        if value > 1000:  # Optional: set a max limit
            raise serializers.ValidationError("Cannot award more than 1000 points at once")
        return value

    def validate_student_id(self, value):
        try:
            user = User.objects.get(id=value, user_type=2)
        except User.DoesNotExist:
            raise serializers.ValidationError("Student not found")
        return value


class AwardPointsResponseSerializer(serializers.Serializer):
    """Serializer for award points response"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    new_balance = serializers.IntegerField()
    transaction = WalletTransactionSerializer()

class TeacherStatsSerializer(serializers.Serializer):
    teacher = serializers.DictField()
    stats = serializers.DictField()
    trends = serializers.DictField()

class RecentTransactionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    studentName = serializers.CharField()
    type = serializers.CharField()
    amount = serializers.IntegerField()
    reason = serializers.CharField()
    timestamp = serializers.CharField()
    teacherAction = serializers.BooleanField()

#HELPERS
def generate_qr_image(qr_value: str):
        """Generate a QR code image with custom colors and zero margins."""
        qr = qrcode.QRCode(
            version=1,  # QR complexity (1 is smallest)
            error_correction=ERROR_CORRECT_H,  # High error correction
            box_size=10,  # Pixel size of each box
            border=0,     # ✅ No white margin around the QR
        )
        qr.add_data(qr_value)
        qr.make(fit=True)

        img = qr.make_image(
            fill_color="white",     # ✅ Foreground color (QR dots)
            back_color="black"      # ✅ Background color
        )
        return img
