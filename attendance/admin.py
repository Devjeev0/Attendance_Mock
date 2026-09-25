"""
Admin configuration for the Attendance app.
"""

from django.contrib import admin

from .models import AttendanceLog, Office


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    """Admin view for Office."""

    list_display = ("name", "allowed_radius_meters")
    search_fields = ("name",)


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    """Admin view for AttendanceLog."""

    list_display = ("user", "status", "distance_meters", "timestamp")
    list_filter = ("status",)
    readonly_fields = ("timestamp",)
