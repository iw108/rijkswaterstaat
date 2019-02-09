

from bs4 import BeautifulSoup
from calendar import timegm
from datetime import datetime
import netCDF4
import os
import pandas as pd
from pytz import utc, timezone
import re
import requests


CATALOG_URL = ('http://opendap.deltares.nl/thredds/'
               'catalog/opendap/rijkswaterstaat/waterbase')

DATA_URL = ('http://opendap.deltares.nl/thredds/'
            'dodsC/opendap/rijkswaterstaat/waterbase/')


def get_files(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    files = []
    for item in soup.find_all('a'):
        if (re.match('(^catalog.html)|(.*catalog.html)$', item.attrs.get('href'))
                and re.match('(^\d{2})|(^id\d+)', item.text)):
            files.append(item.text.strip('/'))
    return files


MEASUREMENTS = []
for file in get_files(os.path.join(CATALOG_URL, 'catalog.html')):
    MEASUREMENTS.append({
        'id': re.findall('(^\d+)', file)[0],
        'parameter': re.findall('^\d+_(.*)', file)[0]
    })


def get_measurement_id(measurement):
    measurement_id = None
    for param in MEASUREMENTS:
        if param['parameter'].lower() == measurement.lower():
            measurement_id = param['id']
            break
    return measurement_id


class Measurement(object):

    def __init__(self, measurement):

        self.measurement = measurement
        self.measurement_id = get_measurement_id(measurement)
        if not self.measurement_id:
            raise ValueError("Measurement doesn't exist.")

        full_name = '_'.join((self.measurement_id, self.measurement))
        self.data_url = os.path.join(DATA_URL, full_name, 'nc')
        self.catalog_url = os.path.join(CATALOG_URL, full_name,
                                        'nc', 'catalog.html')

    @property
    def file_list(self):
        files = [os.path.join(self.data_url, file)
                     for file in get_files(self.catalog_url)]
        return files

    def get_file(self, station_name):
        file_out = None
        station_name = station_name.lower()
        for file in self.file_list:
            station_code = re.findall('id\d+-(.*).nc$', file)[0]
            if all([letter in station_name for letter in station_code.lower()]):
                with netCDF4.Dataset(file, 'r') as ds:
                    if ds.stationname.lower() == station_name.lower():
                        file_out = File(file)
        return file_out

    def get_all_available_stations(self):
        return [File(file).meta for file in self.files]


class File:

    def __init__(self, filepath):
        self.filepath = filepath

    @property
    def meta(self):
        with self.open() as ds:
            station_meta = {
                'station_name': ds.stationname,
                'location_code': ds.locationcode,
                'coordinates': [ds.geospatial_lat_min, ds.geospatial_lon_min],
                'crs': 'epsg:4326'
            }
        return station_meta

    def get_data(self, start_date, end_date):
        expected_tz = timezone('MET')
        start, end = map(lambda t: timegm(expected_tz.localize(t).timetuple()),
                         [start_date, end_date])
        with self.open() as ds:
            timestamps = (ds.variables['time'][:] * 24 * 60).round() * 60
            variable_name = list(ds.variables.keys())[-1]
            variables = ds.variables[variable_name][:].flatten()

        mask = (timestamps >= start) & (timestamps <= end)
        df = pd.DataFrame(variables[mask], index=timestamps[mask],
                          columns=[variable_name])
        df.index = df.index.map(lambda t: expected_tz.localize(datetime.utcfromtimestamp(t)))
        return df

    def open(self):
        return netCDF4.Dataset(self.filepath, 'r')


if __name__ == "__main__":
    measurement = 'Waterhoogte_in_cm_t.o.v._normaal_amsterdams_peil_in_oppervlaktewater'
    waterhoogte = Measurement(measurement)
    file = waterhoogte.get_file('scheveningen')
    print(file.meta)
    print(file.get_data(datetime(2014, 1, 1), datetime(2014, 1, 2)))
