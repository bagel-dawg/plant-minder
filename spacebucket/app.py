from flask import Flask, request, jsonify, render_template, Response, current_app, g
from datetime import datetime, date
import Adafruit_DHT
import atexit
import csv
from apscheduler.scheduler import Scheduler
import os
import logging
from logging import Formatter, FileHandler
import requests
import time
import json
import sqlite3
import click

DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4

starting_date = date(2020, 7, 13)
plant_name = "Aphrodite"

app = Flask(__name__, instance_relative_config=True)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1

logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(os.getenv('DATABASE', '/tmp/spacebucket'))
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():

    with app.app_context():
        db = get_db()

        with app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf8'))
        db.commit()

@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_connection)
    app.cli.add_command(init_db_command)


init_app(app)

cron = Scheduler(daemon=True)
# Explicitly kick off the background thread
cron.start()

@cron.interval_schedule(seconds=5)
def log_environment():

    with app.app_context():
        db = get_db()
        environment = environment_stats()

        if environment['temperature'] is None or environment['humidity'] is None:
            return None

        db.execute(
            "INSERT INTO environment (env_timestamp, temperature, humidity) VALUES (?, ?, ?)", (environment['time'], environment['temperature'], environment['humidity']),
        )
        db.commit()

@app.route('/')
def index():
    environment = requests.get('http://localhost:80/environment_stats').json()

    logger.info(environment)

    return render_template('index.html', plant_name=plant_name, days_since=days_since()['days_since'], temperature=environment['temperature'], humidity=environment['humidity'] )

@app.route('/environment_stats')
def environment_stats():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)

    logger.info('DHT22: Temperature reading: {temp}, Humidity reading: {humid}'.format(temp=temperature, humid=humidity))

    if (temperature > 100) or (temperature is None):
        temperature = None
        logger.info('Temperature reading was over 100 or was none, something is probably wrong...')
    else:
        temperature = (temperature * 9/5) + 32
        temperature = round(temperature,2)

    if humidity > 100 or humidity is None:
        humidity = None
        logger.info('Temperature reading was over 100 or was none, something is probably wrong...')
    else:
        humidity = round(humidity, 2)

    return { 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S') , 'temperature' : str(temperature), 'humidity' : str(humidity) }

@app.route('/days_since')
def days_since():
    return { 'days_since' : str((date.today() - starting_date).days) }

@app.after_request
def add_header(response):
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    return response

atexit.register(lambda: cron.shutdown(wait=False))
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')


