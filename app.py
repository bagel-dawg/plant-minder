from flask import Flask, request, jsonify, render_template
from datetime import datetime, date
import Adafruit_DHT
import atexit
import csv
from apscheduler.scheduler import Scheduler
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4

starting_date = date(2020, 7, 1)
plant_name = "Aphrodite"

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1

cron = Scheduler(daemon=True)
# Explicitly kick off the background thread
cron.start()

@cron.interval_schedule(minutes=5)
def log_environment():
    csv_file_name = 'static/environment_history.csv'

    with open(csv_file_name,"r") as f:
        lines = f.read().splitlines()  # read out the contents of the file

    if len(lines) >= 2016:
       with open(csv_file_name,"w") as f:
            csv_writer = csv.writer(f, delimiter=',')
            for line in lines[1:]:
                csv_writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_NONE, quotechar='', escapechar='\\')
                f.write(line + '\n')
            
            csv_writer.writerow([ datetime.now(), temperature()['temperature'], humidity()['humidity'] ])
    else:
        with open(csv_file_name,"w") as f:
            csv_writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_NONE, quotechar='', escapechar='\\')           
            for line in lines:
                f.write(line + '\n')
            
            csv_writer.writerow([ datetime.now(), temperature()['temperature'], humidity()['humidity'] ])

    f.close()

    df = pd.read_csv(csv_file_name, delimiter=',', 
                         index_col=0, 
                         parse_dates=[0], dayfirst=True, 
                         names=['time','temperature','humidity'])

    fig, ax = plt.subplots()
    ax.plot(df.index, df.values)
    ax.set_xticks(df.index)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter("%Y-%m"))

    df.plot()

    plt.savefig('static/graph.png')

@app.route('/')
def index():
    return render_template('index.html', plant_name=plant_name, days_since=days_since()['days_since'], temperature=temperature()['temperature'], humidity=humidity()['humidity'] )

@app.route('/temperature')
def temperature():
    temperature_reading = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)[1]
    temperature_reading = (temperature_reading * 9/5) + 32
    return { 'temperature' : str(round(temperature_reading,2)) }

@app.route('/humidity')
def humidity():
    return { 'humidity' : str(round(Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)[0],2)) }

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