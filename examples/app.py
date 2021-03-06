#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 19 12:35:46 2019

@author: isaacwilliams
"""

from flask import Flask, render_template, jsonify
from waterinfo.public import Waterinfo

app = Flask(__name__)
app.config['GOOGLE_API_KEY'] = '<YOUR-GOOGLE-API-KEY>'


@app.route('/maps/<measurement>/')
def maps(measurement):
    return render_template('maps.html', measurement=measurement)

@app.route('/api/stations/<measurement>/')
def api(measurement):
    try:
        waterinfo = Waterinfo(measurement)
        waterinfo.update_station_crs('epsg:4326')
        stations = waterinfo.stations
    except ValueError:
        stations = []
    return jsonify(stations)
