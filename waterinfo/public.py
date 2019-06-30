
from datetime import datetime

import pandas as pd
from pytz import utc
import requests

from .utils import Projection


RWS_PUBLIC_MAPS = [
  'waterhoogte-t-o-v-nap',
  'astronomische-getij',
  'waterafvoer',
  'wind',
  'watertemperatuur',
  'stroming',
  'golfhoogte',
]


def get_stations(map_type):
    """
    Get rijkwaterstaat stations
    """

    if map_type not in RWS_PUBLIC_MAPS:
        raise ValueError

    url = 'https://waterinfo.rws.nl/api/point/latestmeasurements?'
    data = requests.get(url, params={'parameterid': map_type}).json()

    # extract station information
    stations = []
    for station in data['features']:
        stations.append({
            'name': station['properties']['name'],
            'locationCode': station['properties']['locationCode'],
            'coordinates': station['geometry']['coordinates'],
            'crs': station['crs']['properties']['name'].lower(),
            'expert_parameter': (
                station['properties']['measurements'][0]['parameterId']
            )
        })
    return stations


class Waterinfo(object):

    api = "http://waterinfo.rws.nl/api/Download/CSV?"

    def __init__(self, map_name):
        if map_name not in RWS_PUBLIC_MAPS:
            raise ValueError(f'{map_name} does not exist')

        self.map_name = map_name
        self.stations = get_stations(self.map_name)

    def update_station_crs(self, crs='epsg:25831'):
        crs_to_change = {stn['crs'] for stn in self.stations} - {crs}
        for old_crs in crs_to_change:
            proj = Projection(crs, old_crs)
            for index, station in enumerate(self.stations):
                if station['crs'] == old_crs:
                    station.update({
                        'crs': crs,
                        'coordinates': (
                            list(proj.backwards(*station['coordinates']))
                        )
                    })

    def get_station(self, station_name):
        """
        Get rijkswaterstaat station information based on station name
        """

        station_info = {}
        for stn in self.stations:
            station_names = [stn['name'].lower(), stn['locationCode'].lower()]
            if station_name.lower() in station_names:
                station_info.update(**stn)
                break
        return station_info

    def get_data_from_horizon(self, station, start_date, end_date):
        """
        Get rijkswaterstaat tidal data for a given station between to
        dates
        """

        # check if full station name provided or slug- if full name get slug
        station = self.get_station(station)
        if not station:
            raise ValueError('Station does not exist')

        # parse input times
        start_offset = (utc.localize(start_date) -
                        utc.localize(datetime.now())).total_seconds()/3600
        end_offset = (utc.localize(end_date) -
                      utc.localize(datetime.now())).total_seconds()/3600
        parameters = {
            'expertParameter': station['expert_parameter'],
            'locationSlug': station['locationCode'],
            'timehorizon': f"{int(start_offset)},{int(end_offset)}"
        }

        response = requests.get(self.api, params=parameters)
        csv = response.text
        return csv


class Waterhoogte(Waterinfo):

    def __init__(self):
        super().__init__('waterhoogte-t-o-v-nap')

    def get_data_between_dates(self, station, start_date, end_date, **kwargs):

        # check if full station name provided or slug- if full name get slug
        station = self.get_station(station)
        if not station:
            raise ValueError('Station does not exist')

        tidal_reference = 'NAP'
        if 'to_nvt' in kwargs:
            tidal_reference = 'NVT'

        date_format = '%Y-%m-%dT%H:%M:%S.001Z'
        parameters = {
            'expertParameter': station['expert_parameter'],
            'locationSlug': station['locationCode'],
            'startdate': utc.localize(start_date).strftime(date_format),
            'enddate': utc.localize(end_date).strftime(date_format),
            'timezone': 'UTC',
            'getijreference': tidal_reference
        }

        response = requests.get(self.api, params=parameters)
        csv = response.text

        if 'parse' in kwargs and kwargs.get('parse') is True:
            return self.parse_csv(csv)
        return csv

    def parse_csv(self, csv):

        # process the the response and store in dataframe
        lines = csv.splitlines()
        timestamps, tidal_level = [], []
        for line in lines[6:]:
            columns = line.split(';')[:-1]

            # Extract date
            timestamps.append(
                datetime.strptime(' '.join(columns[:2]), '%d/%m/%Y %H:%M:%S')
            )

            # extract tidal level
            tidal_level.append(float(columns[-1]))

        df_tidal = pd.DataFrame(
            tidal_level, index=timestamps, columns=['tidal_level']
        )
        df_tidal.index = df_tidal.index.map(lambda ts: utc.localize(ts))
        return df_tidal
