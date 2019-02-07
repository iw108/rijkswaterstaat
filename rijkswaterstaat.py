#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 23 19:50:47 2019

@author: isaacwilliams
"""

import requests
import pyproj
from pytz import utc
from datetime import datetime
import pandas as pd


RWS_MAPS = [
  {'name': 'waterhoogte-t-o-v-nap', 'group': 'Waterhoogten'},
  {'name': 'astronomische-getij', 'group': 'Waterhoogten'},
  {'name': 'waterafvoer', 'group': 'Afvoer'},
  {'name': 'wind', 'group': 'Wind'},
  {'name': 'watertemperatuur', 'group': 'Watertemperatuur'},
  {'name': 'stroming', 'group': 'Stroming'},
  {'name': 'golfhoogte', 'group': 'Golven'},
]


def get_map_info(map_name):
    map_info = {}
    rws_map = [rws_map for rws_map in RWS_MAPS if rws_map['name'] == map_name]
    if rws_map:
        map_info = rws_map[0]
    return map_info


class Projection(object):
    """
    class to transform between two coordinate systems
    """

    def __init__(self, first_projection, second_projection):
        self.first_projection = pyproj.Proj(init=first_projection)
        self.second_projection = pyproj.Proj(init=second_projection)

    def forwards(self, lon, lat):
        """
        transform longitude and latitude from first to second coord system
        """
        return pyproj.transform(self.second_projection, self.first_projection, lon, lat)

    def backwards(self, lon, lat):
        """
        transform longitude and latitude from second to first coord system
        """
        return pyproj.transform(self.second_projection, self.first_projection, lon, lat)


def get_download_parameters(group_name):

    url = 'https://waterinfo.rws.nl/api/nav/downloadgroups'
    download_groups = requests.get(url).json()

    parameters = {}
    for group in download_groups:
        if group['label'].lower() == group_name.lower():
            parameters = group['parameters']
            continue

    if parameters:
        for parameter in parameters:
            parameter.pop('synonyms')

    return parameters


def get_stations(map_type):
    """
    Get rijkwaterstaat stations
    """

    if map_type not in [rws_map['name'] for rws_map in RWS_MAPS]:
        raise ValueError

    url = 'https://waterinfo.rws.nl/api/point/latestmeasurements?'
    data = requests.get(url, params={'parameterid': map_type}).json()

    # extract station information
    stations, crs_of_stations = [], []
    for station in data['features']:
        stations.append({
            'name': station['properties']['name'],
            'locationCode': station['properties']['locationCode'],
            'coordinates': station['geometry']['coordinates'],
            'crs': station['crs']['properties']['name'].lower(),
        })

    return stations


class Waterinfo(object):

    api = "http://waterinfo.rws.nl/api/Download/CSV?"

    def __init__(self, map_name):
        map_info = get_map_info(map_name)
        if not map_info:
            raise ValueError(f'{map_name} does not exist')

        self.map_name = map_info['name']
        self.group = map_info['group']
        self.stations = get_stations(map_info['name'])
        self.parameters = get_download_parameters(self.group)

    @property
    def parameter_slugs(self):
        return [parameter['slug'] for parameter in self.parameters]

    @property
    def parameter_names(self):
        return [parameter['label'] for parameter in self.parameters]

    def update_station_crs(self, crs='epsg:25831'):
        crs_of_stations = [stn['crs'] for station in station]
        crs_to_change = {*crs_of_stations} - {crs}
        for old_crs in crs_to_change:
            proj = Projection(crs, old_crs)
            for index, station in enumerate(self.stations):
                if station['crs'] == old_crs:
                    station.update({
                        'crs': crs,
                        'coordinates': list(proj.backwards(*station['coordinates']))
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

    def get_data_from_horizon(self, station, start_date, end_date, **kwargs):
        """
        Get rijkswaterstaat tidal data for a given station between to
        dates
        """

        # get expert parameter to query
        expert_parameter = kwargs.get('expert_parameter', self.parameter_slugs[0])
        if not expert_parameter in self.parameter_slugs:
            raise ValueError("Expert parameter doen't exist")

        # check if full station name provided or slug- if full name get slug
        station = self.get_station(station)
        if not station:
            raise ValueError('Station does not exist')

        #parse input times
        start_offset = (utc.localize(start_date) -
                            utc.localize(datetime.now())).total_seconds()
        end_offset = (utc.localize(end_date) -
                            utc.localize(datetime.now())).total_seconds()

        parameters = {
            'expertParameter': expert_parameter,
            'locationSlug': station['locationCode'],
            'timehorizon': f"{start_offset/3600:.0f},{end_offset/3600:.0f}"
        }
        response = requests.get(self.api, params=parameters)
        csv = response.text
        return csv


class Waterhoogten(Waterinfo):

    def __init__(self):
        super().__init__('waterhoogte-t-o-v-nap', **kwargs)

    def get_data_between_dates(self, station, start_date, end_date, **kwargs):

        # get expert parameter to query
        expert_parameter = kwargs.get('expert_parameter', self.parameter_slugs[0])
        if not expert_parameter in self.parameter_slugs:
            raise ValueError("Expert parameter doen't exist")

        # check if full station name provided or slug- if full name get slug
        station = self.get_station(station)
        if not station:
            raise ValueError('Station does not exist')

        tidal_reference = 'NAP'
        if 'to_nvt' in kwargs:
            tidal_reference = 'NVT'

        date_format = '%Y-%m-%dT%H:%M:%S.001Z'
        parameters = {
            'expertParameter': expert_parameter,
            'locationSlug': station['locationCode'],
            'startdate': utc.localize(start_date).strftime(date_format),
            'enddate': utc.localize(end_date).strftime(date_format),
            'timezone': 'UTC',
            'getijreference': tidal_reference
        }

        response = requests.get(self.api, params=parameters)
        csv = response.text

        if 'parse' in kwargs and kwargs.get('parse') is True:
            return self.parse(csv)
        return csv

    @staticmethod
    def parse_csv(csv):

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

        df_tidal = pd.DataFrame(tidal_level, index=timestamps, columns=['tidal_level'])
        df_tidal.index = df_tidal.index.map(lambda ts: utc.localize(ts))
        return df_tidal


# if __name__ == "__main__":


    # map_name = 'waterhoogte-t-o-v-nap'
    # waterinfo = Waterinfo(map_name)
    #
    # print(waterinfo.stations)
    #
    # station = waterinfo.stations[0]
    # print(waterinfo.get_data(station['name'],
    #                          start_date=datetime(2019, 1, 1),
    #                          end_date = datetime(2019, 1, 3)))
