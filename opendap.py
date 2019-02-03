
import requests
from bs4 import BeautifulSoup
import re
import os
import netCDF4


def get_files(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    files = []
    for item in soup.find_all('a'):
        if (re.match('(^catalog.html)|(.*catalog.html)$', item.attrs.get('href'))
                and re.match('(^\d{2})|(^id\d+)', item.text)):
            files.append(item.text.strip('/'))
    return files


CATALOG_URL = ('http://opendap.deltares.nl/thredds/'
               'catalog/opendap/rijkswaterstaat/waterbase')

DATA_URL = ('http://opendap.deltares.nl/thredds/'
            'dodsC/opendap/rijkswaterstaat/waterbase/')

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

        measurement_id = get_measurement_id(measurement)
        if not measurement_id:
            raise ValueError("Measurement doesn't exist.")

        self.measurement = measurement
        self.full_name = '_'.join((measurement_id, measurement))

        self.catalog_url = os.path.join(CATALOG_URL, self.full_name, 'nc', 'catalog.html')
        self.files = get_files(self.catalog_url)

    def get_station_codes(self):
        pattern = '^id\d+-(.*).nc$'
        return [re.findall(pattern, file)[0] for file in self.files]

    def get_file_path(self, file):
        if file not in self.files:
            raise ValueError("File Doesn't e")
        return os.path.join(DATA_URL, self.full_name, 'nc', file)

    def get_station_file(self, station_name):
        file_out = None
        station_name = station_name.lower()
        for code, file in zip(self.get_station_codes(), self.files):
            if all([letter in station_name for letter in code.lower()]):
                file_path = self.get_file_path(file)
                with netCDF4.Dataset(file_path, 'r') as ds:
                    if ds.stationname.lower() == station_name.lower():
                        file_out = file_path
        return file_out

    def get_all_available_stations(self):
        pattern = '^id\d+-(.*).nc$'
        stations = []
        for file in self.files:
            file_path = self.get_file_path(file)
            with netCDF4.Dataset(file_path, 'r') as ds:
                stations.append({
                    'full_name': ds.stationname,
                    'short_name': re.findall(pattern, file)[0]
                })
        return stations
