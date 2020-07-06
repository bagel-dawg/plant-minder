from flask import Flask, request, jsonify, render_template
from datetime import datetime, date
import Adafruit_DHT
import atexit
import csv
from apscheduler.scheduler import Scheduler
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from scipy import stats
import os
import logging
from logging import Formatter, FileHandler

DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4

starting_date = date(2020, 7, 1)
plant_name = "Aphrodite"

logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1

cron = Scheduler(daemon=True)
# Explicitly kick off the background thread
cron.start()

@cron.interval_schedule(minutes=5)
def log_environment():
    csv_file_name = 'static/environment_history.csv'

    environment = environment_stats()

    if environment['temperature'] is None or environment['humidity'] is None:
        return None

    with open(csv_file_name,"r") as f:
        lines = f.read().splitlines()  # read out the contents of the file

    if len(lines) >= 2016:
       with open(csv_file_name + "_temp","w+") as f_temp:
            csv_writer = csv.writer(f_temp, delimiter=',')
            for line in lines[1:]:
                csv_writer = csv.writer(f_temp, delimiter=',', quoting=csv.QUOTE_NONE, quotechar='', escapechar='\\')
                f_temp.write(line + '\n')
            
            csv_writer.writerow([ datetime.now(), environment['temperature'], environment['humidity'] ])
    else:
        with open(csv_file_name + "_temp","w+") as f_temp:
            csv_writer = csv.writer(f_temp, delimiter=',', quoting=csv.QUOTE_NONE, quotechar='', escapechar='\\')           
            for line in lines:
                f_temp.write(line + '\n')
             
            csv_writer.writerow([ datetime.now(), environment['temperature'], environment['humidity'] ])

    f.close()
    f_temp.close()

    os.replace(csv_file_name+"_temp", csv_file_name)

    df = pd.read_csv(csv_file_name, delimiter=',', 
                         index_col=0, 
                         parse_dates=[0], dayfirst=True, 
                         names=['time','temperature','humidity'])

    df = df[(np.abs(stats.zscore(df)) < 3).all(axis=1)]

    fig, ax = plt.subplots()
    ax.plot(df.index, df.values)
    ax.set_xticks(df.index)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter("%m-%d"))

    df.plot()

    plt.savefig('static/graph.png')
    plt.close()

@app.route('/')
def index():
    environment = environment_stats()
    return render_template('index.html', plant_name=plant_name, days_since=days_since()['days_since'], temperature=environment['temperature'], humidity=environment['humidity'] )

@app.route('/environment_stats')
def environment_stats():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)

    logger.info('DHT22: Temperature reading: {temp}, Humidity reading: {humid}'.format(temp=temperature, humid=humidity))

    if temperature > 100 or temperature is None:
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

    return { 'temperature' : str(temperature), 'humidity' : str(humidity) }

@app.route('/days_since')
def days_since():
    return { 'days_since' : str((date.today() - starting_date).days) }

@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    return response

atexit.register(lambda: cron.shutdown(wait=False))
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')