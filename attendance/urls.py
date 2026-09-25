"""
URL routing for the Attendance app.

Exposes endpoints for authentication, office listing, attendance marking,
and attendance log retrieval.
"""

from django.urls import path

from .views import (
    AttendanceLogListView,
    LoginView,
    LogoutView,
    MarkAttendanceView,
    OfficeListView,
)

app_name = "attendance"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("offices/", OfficeListView.as_view(), name="office-list"),
    path("mark/", MarkAttendanceView.as_view(), name="mark-attendance"),
    path("logs/", AttendanceLogListView.as_view(), name="attendance-logs"),
]
