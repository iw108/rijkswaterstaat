
from calendar import timegm
from datetime import datetime
import json
import logging, logging.config
import os
import re
import requests

from bs4 import BeautifulSoup
import netCDF4
import pandas as pd
from pytz import timezone

from .settings import DATABASE_URL, CATALOG_URL, DATA_URL, DATA_DIR, LOG_DEFAULT


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

    def open(self, retries=3):
        try:
          return netCDF4.Dataset(self.filepath, 'r')
        except OSError as exception:
            if retries > 0:
                print(f"Retrying {self.filepath}")
                return self.open(retries=retries - 1)
            else:
                raise OSError(exception)


def get_files(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    files = []
    for item in soup.find_all('a'):
        if (re.match('(^catalog.html)|(.*catalog.html)$', item.attrs.get('href'))
                and re.match('(^\d{2})|(^id\d+)', item.text)):
            files.append(item.text.strip('/'))
    return files


def extract_data():
    # configure logging
    logging.config.dictConfig(LOG_DEFAULT)

    # get catalogs
    logging.info('Getting catalogs.')
    try:
        catalog_list = get_files(os.path.join(CATALOG_URL, 'catalog.html'))
    except:
        logging.error("Could not get catalog files")
        raise

    # process catalogs and get catalog files
    logging.info(f"Getting catalog files. ({len(catalog_list)} catalogs)")
    catalogs = []
    for index, file in enumerate(catalog_list):
        catalog = {
          'pk': int(re.findall('(^\d+)', file)[0]),
          'full_name': re.findall('^\d+_(.*)', file)[0]
        }

        full_url = f"{CATALOG_URL}/{catalog['pk']:02d}_{catalog['full_name']}/nc/catalog.html"
        try:
            catalog.update({'files': get_files(full_url)})
        except:
            logging.error("Failed to get files for catalog no. {index + 1}")
            raise

        if catalog['files']:
            catalog.update({'id': int(re.findall('^id(\d+)-', catalog['files'][0])[0])})
            catalogs.append(catalog)
        else:
            logging.warning(f"No catalog files found for {full_url}")

    number_of_files = sum([len(catalog['files']) for catalog in catalogs])
    logging.info(f"Finished getting catalog files. {number_of_files} files")

    # read the files and extract the meta info
    logging.info("Extracting file meta data")
    all_files = []
    for index, catalog in enumerate(catalogs):
        files = catalog.pop('files')
        logging.info(f"Processing {catalog['full_name']}.")

        count = 0
        for file in files:
            file_url = f"{DATA_URL}/{catalog['pk']:02d}_{catalog['full_name']}/nc/{file}"
            try:
                meta = OpendapFile(file_url).meta
                meta.update(catalog_id=catalog['id'])
                all_files.append(meta)
                count += 1
            except Exception as e:
                logging.warning(f"Skipping file {file_url}. Error {e}")

        logging.info((f"Finished with {catalog['full_name']} ({index + 1}/{len(catalogs)})."
                      f"Extracted information from {count}/{len(files)} files"))

        catalogs[index] = catalog


    with open(os.path.join(DATA_DIR, 'catalogs.json'), 'w') as file:
        json.dump(catalogs, file, indent=4)

    with open(os.path.join(DATA_DIR, 'files.json'), 'w') as file:
        json.dump(all_files, file, indent=4)
