########################################################################################################################
#
#
#  	Project     	: 	Water Tank Level Reader
#
#   File            :   level.py
#
#	By              :   George Leonard ( georgelza@gmail.com )
#
#   Created     	:   13 May 2022
#
#   Notes       	:   Change InfluxDB time display mode   precision rfc3339
#
#######################################################################################################################

__author__      = "George Leonard"
__email__       = "georgelza@gmail.com"
__version__     = "0.0.1"


import RPi.GPIO as GPIO
import statistics
import time, sys, os, json
from datetime import datetime

from pprint import pprint
from influxdb import InfluxDBClient 
from apputils import * 


configfile      = os.getenv('CONFIGFILE')
config_params   = get_config_params(configfile)


TRIG = int(config_params['ultrasonic']['trig'])
ECHO = int(config_params['ultrasonic']['echo'])

DEBUGLEVEL      = int(config_params['common']['debuglevel'])
TANK_CAPACITY   = int(config_params['common']['tank_capacity'])                 # Whats the full capacity in Litres of the tank
MEASUREMENT     = config_params['common']['measurement']
TAG             = config_params['common']['tag']        
SLEEP_SECONDS   = int(config_params['ultrasonic']['sleep_seconds'])             # Between measurements
EMPTY_DISTANCE  = int(config_params['ultrasonic']['empty_distance'])            # cm - from sensor to bottom of the tank
SAMPLES         = int(config_params['ultrasonic']['samples'])                   # when measuring, how many samples to take, then we take the middle one.

# Speed of sound constant
# 343 m / sec. is rougly the speed of sound in dry air at 20C
# The speed decreases with temperature and increases a bit with more humidity
# This is a cool, damp basement, so we'll assume 341 m / sec. (15C / 59F with 60%RH)
# Sensor measures round-trip time, so we divide by 2 to get half of that distance
SPEED = int(config_params['ultrasonic']['speed'])

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG ,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)
GPIO.output(TRIG, False)

############# Instantiate a connection to the InfluxDB ##################
db = dict()
db['host']              = config_params['influxdb']['host']
db["port"]              = int(config_params['influxdb']['port'])
db["user"]              = config_params['influxdb']['user']
db["password"]          = config_params['influxdb']['password']
db["dbuser"]            = config_params['influxdb']['dbuser']
db["dbuser_password"]   = config_params['influxdb']['dbuser_password']
db["dbname"]            = config_params['influxdb']['dbname']


############## LETS Start ##############





def db_influx_connect(db):
    print("")
    print("#####################################################################")
    print("")

    print('{time}, Creating connection to InfluxDB... '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    print('{time}, Host     : {host} '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        host = config_params['influxdb']['host']

        ))
    print('{time}, Port     : {port}'.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        port = config_params['influxdb']['port']
        ))
    print('{time}, Database : {database} '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        database = config_params['influxdb']['dbname']
        ))

    try:

        client = InfluxDBClient(host = config_params['influxdb']['host'], port = config_params['influxdb']['port'])
        client.switch_database(database = config_params['influxdb']['dbname'])
        
        print('{time}, Connection to InfluxDB Succeeded... '.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

        print("")
        print("#####################################################################")
        print("")

    except Exception as err:

        print('{time}, Connection to InfluxDB Failed... {err}'.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            err=err
        ))
    
        print("")
        print("#####################################################################")
        print("")

        sys.exit(-1)


    return client
# end def


def insertInflux(client, json_data):

    try:

        response = client.write_points(points=json_data)
        print("Write operation & points: {response} {json_data}".format(
            response=response,
            json_data=json_data,
        ))       

    except Exception as err:
        print('{time}, Write Failed !!!: {err}'.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            err    = err
        ))

# end def


def main(db):

    influx_client = db_influx_connect(db)

    ######## Temporary ########
    TEST_EXECUTED = 0
    TEST_COUNT = 5000

    while True:

        distances = []
        sampleCount = 0
        while sampleCount < SAMPLES:
            # Distance Measurement In Progress

            # Limit sample rate to every 10ms (even though spec recommends 60ms)
            time.sleep(0.06)

            # Send 10uS pulse
            GPIO.output(TRIG, True)
            time.sleep(0.00001)
            GPIO.output(TRIG, False)

            # Waiting for ECHO to go high...
            # Max. wait 1 second using pulse_end as temp variable
            pulse_start = time.time()
            pulse_end = time.time()
            while GPIO.input(ECHO)==0 and pulse_start - pulse_end < 1:
                pulse_start = time.time()

            # Waiting for ECHO to go low... (max. wait 1 second)
            pulse_end = time.time()
            while GPIO.input(ECHO)==1 and pulse_end - pulse_start < 1:
                pulse_end = time.time()

            # Append distance measurement to samples array
            pulse_time = pulse_end - pulse_start
            distances.append(pulse_time * SPEED)
            sampleCount = sampleCount + 1

            if DEBUGLEVEL > 1:

                print('{time}, pulse_time: {pulse_time}, distance: {distance} '.format(
                    time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
                    pulse_time  = pulse_time,
                    distance    = pulse_time * SPEED
                ))

        # Print date/time and median measurment in cm.
        distance = round( statistics.median(distances), 1)

        if distance > EMPTY_DISTANCE:
            distance = EMPTY_DISTANCE

        # Percentage filled
        percentage = 100-((distance * 100)/EMPTY_DISTANCE)
        percentage = round(percentage, 2)
        percentage = percentage

        tTimestamp  = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.localtime(time.time()))
        tLevel      = round(distance, 2)
        tPercentage = round(100-percentage, 2)
        tVolume     = TANK_CAPACITY - ((1-(distance/EMPTY_DISTANCE))*TANK_CAPACITY)

        # select * from "Water-Tank-Levels"
        # select * from "Water-Tank-Levels" where tag ="Council-Tank-Left"
        json_data = [{
            "measurement" : MEASUREMENT,        # select from 
                "tags": {                       # where tank = ""
                    "tank": TAG
                },
                "time" : tTimestamp,
                "fields": {
                    "water_level":      tLevel,             # cm of water in tank
                    "fill_percentage":  tPercentage,        # based on distance and tank depth, percentage full
                    "water_volume":     tVolume,            # based on percentage and tank capacity
                }
            }
        ]

        if DEBUGLEVEL > 0:
            print('{time}, Measurement: {measurement}, Tag: {tag}, H2O Level : {level} cm, Fill Percentage: {percentage}%, Liters in Tank {volume} L '.format(
                time=tTimestamp,
                measurement= MEASUREMENT,
                tag=TAG,
                level = tLevel,
                percentage = tPercentage,
                volume = tVolume
            ))

        if DEBUGLEVEL > 1:

            print("")
            json_formatted_str = json.dumps(json_data, indent=2)
            print(json_formatted_str)
    

        ########################################################################
        # Insert into InfluxDB Database
        insertInflux(influx_client, json_data)

        time.sleep(SLEEP_SECONDS)

        # Temporary
        if TEST_EXECUTED +1 == TEST_COUNT :
            sys.exit(1)
        TEST_EXECUTED = TEST_EXECUTED + 1

# end main 


if __name__ == '__main__':
    
    print("")
    print('{time}, Starting... '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
    ))

    main(db)
# end def


