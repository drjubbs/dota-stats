# -*- coding: utf-8 -*-
"""Utility functions used by multiple scripts in the project. Includes:

    - MatchSerialization
    - Bitmask
    - MLEncoding

See individual methods for more information.
"""

from datetime import datetime
import numpy as np
from dota_stats import meta


class TimeMethods:
    """Methods to handle time string/format mangling"""

    @classmethod
    def get_time_nearest(cls, timestamp, hour=True):
        """Return timestamp and string to nearest hour or day."""

        utc = datetime.utcfromtimestamp(timestamp)
        if hour is True:
            dt_hour = datetime(utc.year, utc.month, utc.day, utc.hour, 0)
        else:
            dt_hour = datetime(utc.year, utc.month, utc.day, 0, 0)
        dt_str = dt_hour.strftime("%Y%m%d_%H%M")
        itime = int((dt_hour - datetime(1970, 1, 1)).total_seconds())

        return itime, dt_str

    @classmethod
    def get_hour_blocks(cls, timestamp, hours):
        """Given `timestamp`, return list of begin and end times on the near
        hour
        going back `hours` from the timestamp."""

        # Timestamps relative to most recent match in database
        time_hr, _ = cls.get_time_nearest(timestamp)

        begin = []
        end = []
        text = []

        for i in range(int(hours)):
            end.append(time_hr - (i - 1) * 3600)
            begin.append(time_hr - i * 3600)
            _, time_str = cls.get_time_nearest(begin[-1])
            text.append(time_str)

        return text, begin, end

