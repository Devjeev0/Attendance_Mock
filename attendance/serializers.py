"""
Serializers for the Attendance Validation API.

Handles input validation for GPS coordinates and office lookup,
ensuring latitude/longitude are within valid WGS 84 ranges.
"""

from rest_framework import serializers


class AttendanceMarkSerializer(serializers.Serializer):
    """
    Validates the incoming attendance mark request.

    Fields:
        office_id: Primary key of the target Office.
        latitude:  GPS latitude  (-90 to 90).
        longitude: GPS longitude (-180 to 180).
        action_type: Either "CHECK_IN" or "CHECK_OUT".
    """

    office_id = serializers.IntegerField(
        min_value=1,
        help_text="Primary key of the Office to check in at",
    )
    latitude = serializers.FloatField(
        help_text="User's GPS latitude (-90 to 90)",
    )
    longitude = serializers.FloatField(
        help_text="User's GPS longitude (-180 to 180)",
    )
    action_type = serializers.ChoiceField(
        choices=["CHECK_IN", "CHECK_OUT"],
        help_text="Type of attendance action",
    )

    def validate_latitude(self, value):
        """Ensure latitude falls within valid WGS 84 range."""
        if not -90 <= value <= 90:
            raise serializers.ValidationError(
                f"Latitude must be between -90 and 90. Got {value}."
            )
        return value

    def validate_longitude(self, value):
        """Ensure longitude falls within valid WGS 84 range."""
        if not -180 <= value <= 180:
            raise serializers.ValidationError(
                f"Longitude must be between -180 and 180. Got {value}."
            )
        return value
