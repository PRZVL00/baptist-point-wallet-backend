# views.py
# ADD THESE IMPORTS AT THE TOP (if not already there)
from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Avg, Count
from datetime import datetime, timedelta
from .models import *
from .serializers import *
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


# ===== LOGIN API =====
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['user_type'] = user.user_type 
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user_type'] = self.user.user_type
        data['username'] = self.user.username
        return data


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


# ===== DASHBOARD API =====
class RecentActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WalletTransaction.objects.filter(
            wallet__user=self.request.user
        ).order_by("-timestamp")[:20]


# ===== STUDENT VIEWSET =====
class StudentViewSet(viewsets.ModelViewSet):
    queryset = DimStudent.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='scan-qr')
    def scan_qr(self, request):
        """
        Custom action to fetch student by QR code
        POST /api/students/scan-qr/
        Body: { "qr_value": "ABC123..." }
        """
        qr_value = request.data.get('qr_value')
        
        if not qr_value:
            return Response(
                {'error': 'QR value is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find student by QR value
            user = User.objects.get(qr_value=qr_value, user_type=2)
            
            # Ensure wallet exists
            Wallet.objects.get_or_create(user=user)
            
            # Serialize and return student data
            serializer = QRStudentSerializer(user, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'Student not found with this QR code'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Server error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='award-points')
    def award_points(self, request):
        """
        Custom action to award points to a student
        POST /api/students/award-points/
        Body: { "student_id": 1, "points": 50, "reason": "Great work!" }
        """
        # Validate input using serializer
        input_serializer = AwardPointsSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(
                {'error': input_serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = input_serializer.validated_data
        student_id = validated_data['student_id']
        points = validated_data['points']
        reason = validated_data['reason']
        
        # Check if requester is a teacher
        teacher = request.user
        if teacher.user_type != 1:  # 1 = Teacher
            return Response(
                {'error': 'Only teachers can award points'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get student user
            student = get_object_or_404(User, id=student_id, user_type=2)
            
            # Get or create wallet
            wallet, _ = Wallet.objects.get_or_create(user=student)
            
            # Update balance
            wallet.balance += points
            wallet.save()
            
            # Create transaction record
            transaction = WalletTransaction.objects.create(
                wallet=wallet,
                amount=points,
                transaction_type='earn',
                description=f"Awarded by {teacher.first_name} {teacher.last_name}: {reason}"
            )
            
            # Create QR scan log
            QRScanLog.objects.create(
                user=student,
                scanned_by=teacher,
                points_given=points
            )
            
            # Update student's last activity
            try:
                student_profile = DimStudent.objects.get(user=student)
                student_profile.last_activity = timezone.now()
                student_profile.save()
            except DimStudent.DoesNotExist:
                pass
            
            # Serialize transaction
            transaction_serializer = WalletTransactionSerializer(transaction)
            
            # Build response
            response_data = {
                'success': True,
                'message': f'Successfully awarded {points} points to {student.first_name} {student.last_name}',
                'new_balance': wallet.balance,
                'transaction': transaction_serializer.data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to award points: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ===== OTHER VIEWSETS =====
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]


# ===== 🆕 TEACHER DASHBOARD STATS =====
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_stats(request):
    """
    Get comprehensive statistics for teacher dashboard
    GET /api/teacher/stats/
    """
    user = request.user
    
    # Ensure user is a teacher
    if user.user_type != 1:
        return Response({'error': 'Only teachers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    # Calculate date ranges
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    
    # Get all students
    all_students = User.objects.filter(user_type=2)
    total_students = all_students.count()
    
    # Active students (students with activity in last 7 days)
    active_students = DimStudent.objects.filter(
        last_activity__gte=week_ago
    ).count()
    
    # Total points awarded by this teacher (from QR scans)
    total_points_awarded = QRScanLog.objects.filter(
        scanned_by=user
    ).aggregate(total=Sum('points_given'))['total'] or 0
    
    # Points awarded this week
    this_week_points = QRScanLog.objects.filter(
        scanned_by=user,
        timestamp__gte=week_ago
    ).aggregate(total=Sum('points_given'))['total'] or 0
    
    # Average student balance
    average_balance = Wallet.objects.filter(
        user__user_type=2
    ).aggregate(avg=Avg('balance'))['avg'] or 0
    
    # Calculate trends (compare with previous week)
    # Active students trend
    prev_week_active = DimStudent.objects.filter(
        last_activity__gte=two_weeks_ago,
        last_activity__lt=week_ago
    ).count()
    active_trend = calculate_trend(active_students, prev_week_active)
    
    # Points awarded trend
    prev_week_points = QRScanLog.objects.filter(
        scanned_by=user,
        timestamp__gte=two_weeks_ago,
        timestamp__lt=week_ago
    ).aggregate(total=Sum('points_given'))['total'] or 0
    points_trend = calculate_trend(this_week_points, prev_week_points)
    
    # Average balance trend (based on transaction volume)
    current_transactions = WalletTransaction.objects.filter(
        timestamp__gte=week_ago,
        transaction_type='earn'
    ).count()
    prev_transactions = WalletTransaction.objects.filter(
        timestamp__gte=two_weeks_ago,
        timestamp__lt=week_ago,
        transaction_type='earn'
    ).count()
    balance_trend = calculate_trend(current_transactions, prev_transactions)
    
    return Response({
        'teacher': {
            'username': user.username,
            'firstName': user.first_name,
            'lastName': user.last_name,
        },
        'stats': {
            'totalStudents': total_students,
            'activeStudents': active_students,
            'totalPointsAwarded': total_points_awarded,
            'thisWeekPoints': this_week_points,
            'averageStudentBalance': round(average_balance, 0),
        },
        'trends': {
            'activeStudents': active_trend,
            'pointsAwarded': points_trend,
            'thisWeekPoints': points_trend,
            'averageBalance': balance_trend,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_transactions(request):
    """
    Get recent transactions for teacher dashboard
    GET /api/teacher/recent-transactions/?limit=10
    """
    user = request.user
    
    # Ensure user is a teacher
    if user.user_type != 1:
        return Response({'error': 'Only teachers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    limit = int(request.GET.get('limit', 10))
    
    # Get recent QR scan logs (teacher's awards)
    recent_scans = QRScanLog.objects.filter(
        scanned_by=user
    ).select_related('user').order_by('-timestamp')[:limit]
    
    transactions = []
    for scan in recent_scans:
        transactions.append({
            'id': scan.id,
            'studentName': f"{scan.user.first_name} {scan.user.last_name}".strip() or scan.user.username,
            'type': 'earn',
            'amount': scan.points_given,
            'reason': 'Teacher awarded points',
            'timestamp': format_timestamp(scan.timestamp),
            'teacherAction': True
        })
    
    return Response(transactions)


# ===== HELPER FUNCTIONS =====
def calculate_trend(current, previous):
    """
    Calculate percentage trend between current and previous values
    """
    if previous == 0:
        return 100 if current > 0 else 0
    
    change = ((current - previous) / previous) * 100
    return round(change, 1)


def format_timestamp(dt):
    """
    Format timestamp in a human-readable way
    """
    now = timezone.now()
    diff = now - dt
    
    if diff.days == 0:
        if diff.seconds < 60:
            return "Just now"
        elif diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    else:
        return dt.strftime("%b %d, %Y")