"""
Models for the GPS-based Attendance Validation system.

Defines two core models:
- Office: Represents a physical office with a GPS location and geofence radius.
- AttendanceLog: Records each attendance attempt with spatial distance data.
"""

from django.db import models
from django.contrib.auth.models import User


class Office(models.Model):
    """
    Represents a physical office location with a configurable geofence.

    Stores latitude and longitude as decimal fields.
    The `allowed_radius_meters` defines the maximum distance (in meters)
    a user can be from the office and still be marked PRESENT.
    """

    name = models.CharField(max_length=255, help_text="Human-readable office name")
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, help_text="Office GPS latitude"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, help_text="Office GPS longitude"
    )
    allowed_radius_meters = models.IntegerField(
        default=100,
        help_text="Maximum allowed distance in meters for valid attendance",
    )

    class Meta:
        indexes = [
            models.Index(fields=["latitude", "longitude"], name="idx_office_lat_lon"),
        ]

    def __str__(self):
        return self.name


class AttendanceLog(models.Model):
    """
    Records every attendance check-in attempt.

    Stores the user's submitted GPS location, the computed distance
    to the office, and the resulting status (PRESENT or REJECTED).
    """

    STATUS_CHOICES = [
        ("PRESENT", "Present"),
        ("REJECTED", "Rejected"),
    ]
    
    ACTION_CHOICES = [
        ("CHECK_IN", "Check In"),
        ("CHECK_OUT", "Check Out"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="attendance_logs",
        help_text="The user who attempted to mark attendance",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Server-side timestamp of the attendance attempt",
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, help_text="User's GPS latitude"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, help_text="User's GPS longitude"
    )
    distance_meters = models.FloatField(
        help_text="Calculated distance in meters from the office",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        help_text="Attendance result: PRESENT if within radius, else REJECTED",
    )
    action_type = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
        default="CHECK_IN",
        help_text="Whether this was a check-in or check-out",
    )

    class Meta:
        indexes = [
            models.Index(fields=["latitude", "longitude"], name="idx_log_lat_lon"),
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.username} — {self.get_action_type_display()} {self.status} at {self.timestamp:%Y-%m-%d %H:%M}"
