"""Export utilities for CSV and JSON."""

import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List


class ExportUtility:
    """Utility class for exporting data."""

    @staticmethod
    def to_csv(data: List[Dict[str, Any]], columns: List[str] = None) -> str:
        """Export data to CSV format.

        Args:
            data: List of dictionaries to export
            columns: Optional list of columns to include (defaults to all keys)

        Returns:
            CSV string
        """
        if not data:
            return ""

        # Determine columns
        if columns is None:
            columns = list(data[0].keys())

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")

        # Write header
        writer.writeheader()

        # Write rows
        for row in data:
            # Convert datetime objects to strings
            clean_row = {}
            for key, value in row.items():
                if key in columns:
                    if isinstance(value, datetime):
                        clean_row[key] = value.isoformat()
                    elif value is None:
                        clean_row[key] = ""
                    else:
                        clean_row[key] = str(value)
            writer.writerow(clean_row)

        return output.getvalue()

    @staticmethod
    def to_json(data: List[Dict[str, Any]], pretty: bool = False) -> str:
        """Export data to JSON format.

        Args:
            data: List of dictionaries to export
            pretty: Whether to pretty-print the JSON

        Returns:
            JSON string
        """

        def json_serializer(obj):
            """JSON serializer for objects not serializable by default."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        if pretty:
            return json.dumps(data, indent=2, default=json_serializer)
        return json.dumps(data, default=json_serializer)

    @staticmethod
    def generate_filename(base_name: str, extension: str) -> str:
        """Generate filename with timestamp.

        Args:
            base_name: Base name for the file
            extension: File extension (without dot)

        Returns:
            Filename with timestamp
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base_name}_{timestamp}.{extension}"
