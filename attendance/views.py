"""
Views for the GPS-based Attendance Validation API.

Provides endpoints for:
1. Marking attendance with GPS coordinates (POST /api/attendance/mark/)
2. Listing available offices (GET /api/attendance/offices/)
3. Viewing the authenticated user's attendance logs (GET /api/attendance/logs/)
4. User login via session auth (POST /api/attendance/login/)
5. User logout (POST /api/attendance/logout/)
"""
import math
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from rest_framework import status
import os
from dotenv import dotenv_values
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AttendanceLog, Office
from .serializers import AttendanceMarkSerializer


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in meters between two points
    on the earth (specified in decimal degrees).
    """
    R = 6371000  # radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class LoginView(APIView):
    """
    POST /api/attendance/login/

    Authenticate a user and create a session.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return Response(
                {"status": "SUCCESS", "username": user.username},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"status": "FAILED", "message": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class LogoutView(APIView):
    """
    POST /api/attendance/logout/

    End the current user session.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(
            {"status": "SUCCESS", "message": "Logged out"},
            status=status.HTTP_200_OK,
        )


class OfficeListView(APIView):
    """
    GET /api/attendance/offices/

    Return a list of all registered offices with their coordinates and radius.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        env_config = dotenv_values(os.path.join(settings.BASE_DIR, '.env'))
        env_lat = float(env_config.get('OFFICE_LATITUDE', 13.0827))
        env_lon = float(env_config.get('OFFICE_LONGITUDE', 80.2707))
        
        offices = Office.objects.all()
        data = [
            {
                "id": office_obj.id,
                "name": "My Office (From .env)", # Override name so they know it's working
                "latitude": env_lat,
                "longitude": env_lon,
                "allowed_radius_meters": office_obj.allowed_radius_meters,
            }
            for office_obj in offices
        ]
        return Response(data, status=status.HTTP_200_OK)


class AttendanceLogListView(APIView):
    """
    GET /api/attendance/logs/

    Return the authenticated user's attendance history, newest first.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = AttendanceLog.objects.filter(user=request.user).order_by("-timestamp")[:50]
        data = [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "latitude": float(log.latitude),
                "longitude": float(log.longitude),
                "distance_meters": log.distance_meters,
                "status": log.status,
                "action_type": log.action_type,
            }
            for log in logs
        ]
        return Response(data, status=status.HTTP_200_OK)


class MarkAttendanceView(APIView):
    """
    POST /api/attendance/mark/

    Mark attendance by submitting GPS coordinates. The server calculates
    the distance to the specified office and records the result.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AttendanceMarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        office_id = serializer.validated_data["office_id"]
        latitude = serializer.validated_data["latitude"]
        longitude = serializer.validated_data["longitude"]
        action_type = serializer.validated_data["action_type"]

        # ── Look up the office ──
        try:
            office = Office.objects.get(pk=office_id)
        except Office.DoesNotExist:
            return Response(
                {"status": "FAILED", "message": f"Office with id {office_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Compute geodesic distance via Haversine formula ──
        env_config = dotenv_values(os.path.join(settings.BASE_DIR, '.env'))
        env_lat = float(env_config.get('OFFICE_LATITUDE', 13.0827))
        env_lon = float(env_config.get('OFFICE_LONGITUDE', 80.2707))

        distance_meters = round(haversine(
            latitude, longitude, 
            env_lat, env_lon
        ), 2)

        # ── Determine attendance status ──
        is_within_radius = distance_meters <= office.allowed_radius_meters
        attendance_status = "PRESENT" if is_within_radius else "REJECTED"
        
        # ── State Validation (Prevent double check-ins/check-outs) ──
        if attendance_status == "PRESENT":
            today = timezone.now().date()
            last_successful_log = AttendanceLog.objects.filter(
                user=request.user,
                timestamp__date=today,
                status="PRESENT"
            ).order_by('-timestamp').first()

            if action_type == "CHECK_IN":
                if last_successful_log and last_successful_log.action_type == "CHECK_IN":
                    return Response(
                        {"status": "FAILED", "message": "You are already checked in today.", "distance_meters": distance_meters},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif action_type == "CHECK_OUT":
                if not last_successful_log or last_successful_log.action_type == "CHECK_OUT":
                    return Response(
                        {"status": "FAILED", "message": "You cannot check out before checking in.", "distance_meters": distance_meters},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # ── Atomically log the attempt ──
        with transaction.atomic():
            AttendanceLog.objects.create(
                user=request.user,
                latitude=latitude,
                longitude=longitude,
                distance_meters=distance_meters,
                status=attendance_status,
                action_type=action_type,
            )

        # ── Build response ──
        if is_within_radius:
            return Response(
                {
                    "status": "SUCCESS",
                    "message": "Attendance marked successfully",
                    "distance_meters": distance_meters,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "FAILED",
                "message": "Out of allowed radius",
                "distance_meters": distance_meters,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
