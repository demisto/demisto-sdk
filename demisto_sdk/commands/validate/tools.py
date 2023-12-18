from datetime import datetime

from demisto_sdk.commands.common.constants import ISO_TIMESTAMP_FORMAT


def check_timestamp_format(timestamp):
        """Check that the timestamp is in ISO format"""
        try:
            datetime.strptime(timestamp, ISO_TIMESTAMP_FORMAT)
            return True
        except ValueError:
            return False