
import requests
from bs4 import BeautifulSoup
import re
import os


def get_files(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    files = []
    for item in soup.find_all('a'):
        if (re.match('(^catalog.html)|(.*catalog.html)$', item.attrs.get('href'))
                and re.match('(^\d{2})|(^id\d+)', item.text)):
            files.append(item.text.strip('/'))
    return files


BASE_URL = 'http://opendap.deltares.nl/thredds/catalog/opendap/rijkswaterstaat/waterbase'

MEASUREMENTS = []
for file in get_files(os.path.join(BASE_URL, 'catalog.html')):
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

        self.catalog_url = os.path.join(BASE_URL, self.full_name, 'nc', 'catalog.html')
        self.files = get_files(self.catalog_url)

    def get_available_stations(self):
        pattern = '^id\d+-(.*).nc$'
        stations = map(lambda file: re.search(pattern, file).group(), self.files)
        return list(stations)

    def get_file_path(self, file):
        if file not in self.files:
            return ValueError("File doesn't exist.")
        return os.path.join(BASE_URL, self.full_name, 'nc', file)
