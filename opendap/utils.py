
from calendar import timegm
from datetime import datetime

import netCDF4
import pandas as pd
from pytz import timezone

from .settings import TIMEZONE


class OpendapFile:

    def __init__(self, filepath):
        self.filepath = filepath

    @property
    def meta(self):
        with self.open() as ds:
            station_meta = {
                'station_name': ds.stationname,
                'location_code': ds.locationcode,
                'lat': ds.geospatial_lat_min,
                'lon': ds.geospatial_lon_min,
                'epsg': '4326',
                'time_coverage_start': ds.time_coverage_start,
                'time_coverage_end': ds.time_coverage_end
            }
        return station_meta

    def get_data(self, start_date, end_date):
        expected_tz = timezone(TIMEZONE)
        start, end = map(lambda t: timegm(expected_tz.localize(t).timetuple()),
                         [start_date, end_date])
        with self.open() as ds:
            timestamps = (ds.variables['time'][:] * 24 * 60).round() * 60
            variable_name = list(ds.variables.keys())[-1]
            variables = ds.variables[variable_name][:].flatten()

        mask = (timestamps >= start) & (timestamps <= end)
        df = pd.DataFrame(variables[mask], index=timestamps[mask],
                          columns=[variable_name])
        df.index = df.index.map(
            lambda t: expected_tz.localize(datetime.utcfromtimestamp(t))
        )
        return df

    def open(self, retries=3):
        try:
            return netCDF4.Dataset(self.filepath, 'r')
        except OSError as exception:
            if retries > 0:
                print(f"Retrying {self.filepath}")
                return self.open(retries=retries - 1)
            else:
                raise OSError(exception)
