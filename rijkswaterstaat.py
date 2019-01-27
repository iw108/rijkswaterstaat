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


def get_stations(map_type, **kwargs):
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
        crs_of_stations.append(stations[-1]['crs'])

    # get coordinate system of stations
    crs = kwargs.get('crs', 'epsg:25831')
    crs_to_change = {*crs_of_stations} - {crs}
    if crs_to_change:
        for old_crs in crs_to_change:
            proj = Projection(crs, old_crs)
            for station in stations:
                if station['crs'] == old_crs:
                    station.update({
                        'crs': crs,
                        'coordinates': list(proj.backwards(*station['coordinates']))
                    })
    return stations


class Waterinfo(object):

    def __init__(self, map_name, **kwargs):
        map_info = get_map_info(map_name)
        if not map_info:
            raise ValueError(f'{map_name} does not exist')

        self.map_name = map_info['name']
        self.group = map_info['group']
        self.stations = get_stations(map_info['name'], **kwargs)
        self.expert_parameters = get_download_parameters(self.group)

    def get_station(self, station_name):
        """
        Get rijkswaterstaat station information based on station name
        """

        # create empty station
        station = {
            'name': station_name,
            'locationCode': None,
            'coordinates': None,
            'crs': None
        }

        for stn in self.stations:
            if stn['name'].lower() == station_name.lower():
                station.update(**stn)
                continue
        return station

    def get_data(self, station, start_date, end_date, **kwargs):
        """
        Get rijkswaterstaat tidal data for a given station between to
        dates
        """

        # check if full station name provided or slug- if full name get slug
        if station.endswith(')'):
            station_slug = station
        else:
            station_slug = self.get_station(station)['locationCode']

        # get expert parameter to query
        expert_parameter = kwargs.get('expert_parameter',
                                      self.expert_parameters[0]['slug'])
        if 'expert_parameter' in kwargs:
            if not [parameter for parameter in self.expert_parameters
                        if parameter['slug'] == expert_parameter]:
                raise ValueError("Expert paramter doen't exist")

        parameters = {
                'expertParameter': expert_parameter,
                'locationSlug': station_slug
        }

        if self.group is not 'Waterhoogten':
            start_offset = (utc.localize(start_date) -
                               utc.localize(datetime.now())).total_seconds()
            end_offset = (utc.localize(end_date) -
                               utc.localize(datetime.now())).total_seconds()

            parameters.update({
                'timehorizon': f"{start_offset/3600:.0f},{end_offset/3600:.0f}"
            })
        else:
            tidal_reference = 'NAP'
            if 'to_nvt' in kwargs:
                tidal_reference = 'NVT'

            date_format = '%Y-%m-%dT%H:%M:%S.001Z'
            parameters.update({
                 'startdate': utc.localize(start_date).strftime(date_format),
                 'enddate': utc.localize(end_date).strftime(date_format),
                 'timezone': 'UTC',
                 'getijreference': tidal_reference
            })

        # query api and get data
        url = "http://waterinfo.rws.nl/api/Download/CSV?"
        response = requests.get(url, params=parameters)

        return response.text


def parse_tidal_csv(csv_text):

    # process the the response and store in dataframe
    lines = csv_text.splitlines()
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


if __name__ == "__main__":
    map_name = 'waterhoogte-t-o-v-nap'
    waterinfo = Waterinfo(map_name)

    print(waterinfo.stations)

    station = waterinfo.stations[0]
    print(waterinfo.get_data(station['name'],
                             start_date=datetime(2019, 1, 1),
                             end_date = datetime(2019, 1, 3)))
