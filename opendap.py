
import requests
from bs4 import BeautifulSoup
import re
import os
import netCDF4


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

        measurement_id = get_measurement_id(measurement)
        if not measurement_id:
            raise ValueError("Measurement doesn't exist.")

        self.measurement = measurement
        self.full_name = '_'.join((measurement_id, measurement))
        self.catalog_url = os.path.join(CATALOG_URL, self.full_name,
                                        'nc', 'catalog.html')

    @property
    def files(self):
        files = [os.path.join(DATA_URL, self.full_name, 'nc', file)
                     for file in get_files(self.catalog_url)]
        return files

    def get_station_codes(self):
        pattern = 'id\d+-(.*).nc$'
        return [re.findall(pattern, file)[0] for file in self.files]

    def get_station_file(self, station_name):
        file_out = None
        station_name = station_name.lower()
        for code, file in zip(self.get_station_codes(), self.files):
            if all([letter in station_name for letter in code.lower()]):
                with netCDF4.Dataset(file, 'r') as ds:
                    if ds.stationname.lower() == station_name.lower():
                        file_out = file
        return file_out

    def get_all_available_stations(self):
        stations = []
        for file in self.files:
            with netCDF4.Dataset(file_path, 'r') as ds:
                stations.append({
                    'station_name': ds.stationname,
                    'location_code': ds.locationcode,
                    'coordinates': [ds.geospatial_lat_min, ds.geospatial_lon_min],
                    'crs': 'epsg:4326'
                })
        return stations


class File:

    def __init__(self, filepath):
        self.filepath = self.filepath

    def get_file_meta(self):
        with self.open() as ds:
            station = {
                'station_name': ds.stationname,
                'location_code': ds.locationcode,
                'coordinates': [ds.geospatial_lat_min, ds.geospatial_lon_min],
                'crs': 'epsg:4326'
            }
        return station

    def get_data(self, start_date, end_date):
        with self.open() as ds:
            t = ds.variables['time']
        return t

    def open(self):
        return netCDF4.Dataset(self.file_path, 'r')


if __name__ == "__main__":
    print(MEASUREMENTS)
    measurement = 'Totaal_fosfaat_in_mg_l_na_filtratie_in_oppervlaktewater'
    x = Measurement(measurement)
    print(x.get_station_codes())
    print(x.files)
