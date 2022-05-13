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
#   Notes       	:
#
#######################################################################################################################
__author__      = "George Leonard"
__email__       = "georgelza@gmail.com"
__version__     = "0.0.1"


import RPi.GPIO as GPIO
import time
from datetime import datetime
from pprint import pprint
import statistics

TRIG = 14
ECHO = 15

DEBUGLEVEL      = 0
TANK_CAPACITY   = 5000  # Litres
MQTT_SERVER     = "172.16.10.21" #
MQTT_USER       = "mqtt_dev" #
MQTT_PW         = "xxxx" #
TANK_NAME       = "Council-water-left#1"
SLEEP_SECONDS   = 5
EMPTY_DISTANCE  = 50  # cm
SAMPLES         = 10

# Speed of sound constant
# 343 m / sec. is rougly the speed of sound in dry air at 20C
# The speed decreases with temperature and increases a bit with more humidity
# This is a cool, damp basement, so we'll assume 341 m / sec. (15C / 59F with 60%RH)
# Sensor measures round-trip time, so we divide by 2 to get half of that distance
SPEED = 17050

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG ,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)
GPIO.output(TRIG, False)

############## LETS Start ##############

   
print('{time}, Starting... '.format(
    time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
))

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
    percentage = str(percentage)

    tTimestamp  = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    tLevel      = round(distance, 2)
    tPercentage = percentage
    tVolume     = (1-(distance/EMPTY_DISTANCE))*TANK_CAPACITY

    json_data = {
        "date_time":    tTimestamp,
        "tank_name":    TANK_NAME,
        "level":        tLevel,             # cm
        "percentage":   tPercentage,        # based on distance and tank depth
        "volume":       tVolume             # based on percentage and tank capacity
    }

    if DEBUGLEVEL > 1:
        print('{time}, Payload: {json_data}'.format(
            time=tTimestamp,
            json_data=json_data
    ))

    print('{time}, Tank: {tank}, Level : {level} cm, Percentage: {percentage}%, Liters {volume} L '.format(
        time=tTimestamp,
        tank= TANK_NAME,
        level = tLevel,
        percentage = tPercentage,
        volume = tVolume
    ))

    # Push to MQTT which forward to InfluxDB via Node-Red

    print("")    
    time.sleep(SLEEP_SECONDS)

