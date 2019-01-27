#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 19 12:35:46 2019

@author: isaacwilliams
"""

from flask import Flask, render_template, jsonify
from rijkswaterstaat import get_stations

app = Flask(__name__)
app.config['GOOGLE_API_KEY'] = '<YOUR-GOOGLE-API-KEY>'


@app.route('/maps/<measurement>/')
def maps(measurement):
    return render_template('maps.html', measurement=measurement)

@app.route('/api/stations/<measurement>/')
def api(measurement):
    try:
        stations = get_stations(measurement, crs='epsg:4326')
    except ValueError:
        stations = []
    return jsonify(stations)
