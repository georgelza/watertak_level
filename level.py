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
#   git url         :   https://github.com/georgelza/watertak_level
#
#
#					:	select * from WaterTankLevels where ("tank" = 'CouncilWaterTank1')
#
#					:	How to add script to systemd to auto start when pi starts.
#					:	https://www.dexterindustries.com/howto/run-a-program-on-your-raspberry-pi-at-startup/
#
#                   :   cp councilwatertank.service /lib/systemd/system
#                   :   cp rainwatertank.service /lib/systemd/system
#
#                   :    sudo systemctl daemon-reload
#
#                   :    sudo systemctl enable councilwatertank.service
#                   :    sudo systemctl enable rainwatertank.service
#
#                   :    sudo systemctl start councilwatertank.service
#                   :    sudo systemctl start rainwatertank.service
#
#                   :    sudo systemctl status councilwatertank.service
#                   :    sudo systemctl status rainwatertank.service
#
#######################################################################################################################

__author__      = "George Leonard"
__email__       = "georgelza@gmail.com"
__version__     = "0.0.1"
__copyright__   = "Copyright 2022, George Leonard"


import RPi.GPIO as GPIO
import statistics
import time, sys, os, json
from datetime import datetime
from pprint import pprint
from influxdb import InfluxDBClient 
from apputils import * 
import paho.mqtt.client as mqtt
import logging


configfile      = os.getenv('CONFIGFILE')
config_params   = get_config_params(configfile)

DEBUGLEVEL  = int(config_params['common']['debuglevel'])
LOGLEVEL    = config_params['common']['loglevel'].upper()
TRIG        = int(config_params['ultrasonic']['trig'])
ECHO        = int(config_params['ultrasonic']['echo'])
LOGFILE     = config_params['common']['logfile'].lower()

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG ,GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Set up root logger, and add a file handler to root logger
#my_logger.basicConfig(filename='watertanklevel.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

FORMAT = '%(levelname)s :%(message)s'
logging.basicConfig(filename=LOGFILE, 
    filemode='w', 
    encoding='utf-8',
    level = logging.INFO,
    format= FORMAT)

# create logger
my_logger = logging.getLogger(__name__)
# create console handler and set level to debug
my_logger_shandler = logging.StreamHandler()
my_logger.addHandler(my_logger_shandler)

print_params(configfile, my_logger)


if LOGLEVEL == 'INFO':
    my_logger.setLevel(logging.INFO)
    my_logger.info('INFO LEVEL Activated')

elif LOGLEVEL == 'DEBUG':
    my_logger.setLevel(logging.DEBUG)
    my_logger.info('DEBUG LEVEL Activated')

elif LOGLEVEL == 'CRITICAL':
    my_logger.setLevel(logging.CRITICAL)
    my_logger.info('CRITICAL LEVEL Activated')


########################################################################################################################
#
#   Ok Lets start things
#
########################################################################################################################


############# Instantiate a connection to the InfluxDB ##################
def db_influx_connect():

    my_logger.info("")
    my_logger.info("#####################################################################")
    my_logger.info("")

    my_logger.info('{time}, Creating connection to InfluxDB... '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    my_logger.info('{time}, Host     : {host} '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        host = config_params['influxdb']['host']
        ))

    my_logger.info('{time}, Port     : {port}'.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        port = config_params['influxdb']['port']
        ))

    my_logger.info('{time}, Database : {database} '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        database = config_params['influxdb']['dbname']
        ))

    try:

        client = InfluxDBClient(host = config_params['influxdb']['host'], port = config_params['influxdb']['port'])
        client.switch_database(database = config_params['influxdb']['dbname'])
        
        my_logger.info('{time}, Connection to InfluxDB Succeeded... '.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

        my_logger.info("")
        my_logger.info("#####################################################################")
        my_logger.info("")

    except Exception as err:
        my_logger.error('{time}, Connection to InfluxDB Failed... {err}'.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            err=err
        ))

        my_logger.error("")
        my_logger.error("#####################################################################")
        my_logger.error("")

        sys.exit(-1)

    return client
# end def


def insertInflux(client, json_data):

    try:

        response = client.write_points(points=json_data)
        
        my_logger.debug("{time}, InfluxDB Write operation: {response}".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            response=response,
        ))   

    except Exception as err:
        my_logger.error('{time}, Write Failed !!!: {err}'.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            err    = err
        ))

# end def

############# Instantiate/configure a connection to the MQTT Broker ##################


############# Instantiate a connection to the InfluxDB ##################
def mqtt_connect():

    # Configure the Mqtt connection etc.
    broker      = config_params["mqtt"]["broker"]
    port        = int(config_params["mqtt"]["port"])
    clienttag   = config_params["mqtt"]["clienttag"]
    username    = config_params["mqtt"]["username"]
    password    = config_params["mqtt"]["password"]
    base_topic  = config_params['mqtt']['base_topic']

    my_logger.info('{time}, Creating connection to MQTT... '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    my_logger.info('{time}, Broker     : {broker} '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        broker = broker
        ))

    my_logger.info('{time}, Port       : {port}'.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        port = port
        ))

    my_logger.info('{time}, Client Tag : {clienttag} '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        clienttag = clienttag
        ))

    my_logger.info('{time}, Base Topic : {base_topic} '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        base_topic = base_topic
        ))
        
    mqtt.Client.connected_flag      = False                     # this creates the flag in the class
    mqtt.Client.bad_connection_flag = False                     # this creates the flag in the class

    client = mqtt.Client(clienttag)                             # create client object client1.on_publish = on_publish #assign function to callback
                                                                    # client1.connect(broker,port) #establish connection client1.publish("house/bulb1","on")

    ##### Bind callback functions
    client.on_connect       = on_connect                        # bind my on_connect to client
    client.on_log           = on_log                            # bind my on_log to client
    client.on_message       = on_message                        # bind my on_message to client
    client.on_disconnect    = on_disconnect
    client.on_publish       = on_publish
    client.on_subscribe     = on_subscribe

    try:
        client.username_pw_set(username, password)
        client.connect(broker, port)                                          # connect
        my_logger.info("{time}, Connected to to MQTT Broker: {broker}, Port: {port}".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            broker=broker,
            port=port
        ))

        my_logger.info("")
        my_logger.info("#####################################################################")
        my_logger.info("")

    except Exception as err:
        my_logger.error("{time}, Connection to MQTT Failed... {broker}, Port: {port}, Err: {err}".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            broker=broker,
            port=port,
            err=err
        ))

        my_logger.error("")
        my_logger.error("#####################################################################")
        my_logger.error("")

        #influx_client.close()
        GPIO.cleanup()
        sys.exit(1)

    return client
# end def

#define callbacks
def on_connect(client, userdata, flags, rc):

    if rc == 0:
        client.connected_flag = True

        if DEBUGLEVEL > 2: 
            my_logger.debug("MQTT connected OK")

    else:
        my_logger.error("MQTT Bad connection Returned code=", rc)

        client.bad_connection_flag = True


def on_log(client, userdata, level, buf):

    if DEBUGLEVEL > 2: 
        my_logger.debug("log : " + buf)

def on_message(client, userdata, message):

    topic = message.topic
    m_decode = str(message.payload.decode("utf-8"))

    if DEBUGLEVEL > 2: 
        my_logger.debug('received message : {time}, {topic}, {payload}'.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            topic=topic,
            payload=json.dumps(m_decode, indent=2, sort_keys=True)))

def on_publish(client, userdata, mid):

    if DEBUGLEVEL > 2: 
        my_logger.debug("In on_pub callback mid= ", mid)

def on_subscribe(client, userdata, mid, granted_qos):

    if DEBUGLEVEL > 2: 
        my_logger.debug("subscribed")

def on_disconnect(client, userdata, flags, rc=0):

    if DEBUGLEVEL > 2: 
        my_logger.debug("Disconnected flags result code " + str(rc)+" client_id")

    client.connected_flag = False


def publishMQTT(client, json_data):

    base_topic  = config_params["mqtt"]["base_topic"]

    try:

        ret = client.publish(base_topic + "/json", json.dumps(json_data), 0)           # QoS = 0
        my_logger.debug("{time}, MQTT Publish returned: {ret}".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            ret=ret
        ))    

    except Exception as err:
        my_logger.error('{time}, Publish Failed !!!: {err}'.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            err    = err
        ))

# end def

############# General calculations ##################

# measure distance to water surface
def distance():

    if DEBUGLEVEL > 2: 
        my_logger.debug("{time}, Entering distance: ".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    speed = int(config_params["ultrasonic"]["speed"])

    # set Trigger to HIGH
    GPIO.output(TRIG, True)
    time.sleep(0.00001)         # set Trigger after 0.01ms to LOW
    GPIO.output(TRIG, False)
 
    # save pulse_start
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
 
    # save time of arrival
    while GPIO.input(ECHO) == 1:
        pulse_stop = time.time()
 
    pulse_time = pulse_stop - pulse_start       # time difference between signal send and signal recieve

    distance = round(pulse_time * speed, 2)

    if DEBUGLEVEL > 2: 
        my_logger.debug("{time}, Exiting distance: ".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    return pulse_time, distance
# end def


# Return median measurement of the samples taken
def middistance():

    if DEBUGLEVEL > 2: 
        my_logger.debug("{time}, Entering middistance: ".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    samples                 = int(config_params["ultrasonic"]["samples"])
    samples_sleep_seconds   = float(config_params["ultrasonic"]["sample_sleep_seconds"])

    runs=[]
    for i in range(samples):

        pulse_time, meassured_distance = distance()
        runs.append(meassured_distance)

        if DEBUGLEVEL > 1:
            my_logger.debug('{time}, pulse_time: {pulse_time}, distance: {distance} '.format(
                time        = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
                pulse_time  = pulse_time,
                distance    = meassured_distance
            ))

        time.sleep(samples_sleep_seconds)

    middistance = statistics.median(runs)

    if DEBUGLEVEL > 2: 
        my_logger.debug("{time}, Exiting middistance: ".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    return round(middistance, 2)
# end def 


# Height of water in tank
def waterheight(dist_to_water):           #  

    if DEBUGLEVEL > 2: 
        my_logger.debug("{time}, Entering waterheight: ".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    total_tank_deph     = int(config_params["ultrasonic"]["total_tank_deph"])
    waterheight         = total_tank_deph - dist_to_water

    if DEBUGLEVEL > 2: 
        my_logger.debug("{time}, Exiting waterheight: ".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    return round(waterheight, 2)
# end def


 # water level as % (percentage) of tank 
def filledpercenatge(waterheight):               

    if DEBUGLEVEL > 2: 
        my_logger.debug("{time}, Entering filledpercenatge: ".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    total_tank_deph     = int(config_params["ultrasonic"]["total_tank_deph"])
    buffer_distance     = int(config_params["ultrasonic"]["buffer_distance"])
    percentage          = waterheight / (total_tank_deph - buffer_distance)

    if DEBUGLEVEL > 2: 
        my_logger.debug("{time}, Exiting filledpercenatge: ".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    return round(percentage, 2)
# end def


def watervolume(filledpercenatge):               

    if DEBUGLEVEL > 2: 
        my_logger.debug("{time}, Entering watervolume: ".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    tank_capacity   = int(config_params["common"]["tank_capacity"])
    watervolume     = tank_capacity * filledpercenatge

    if DEBUGLEVEL > 2: 
        my_logger.debug("{time}, Exiting watervolume: ".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    return round(watervolume, 2)
# end def


def main():

    if DEBUGLEVEL > 2: 
        my_logger.debug("{time}, Entering main(): ".format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

    measurement     = config_params["common"]["measurement"]
    tag             = config_params["common"]["tag"]
    sleep_seconds   = int(config_params["ultrasonic"]["sleep_seconds"])
    total_tank_deph = int(config_params["ultrasonic"]["total_tank_deph"])
    
    try: 
        # Create the InfluxDB connection
        influx_client = db_influx_connect()

        # Create the MQTT connection
        client = mqtt_connect()
        
        run_flag = True
        while run_flag == True:
            
            distance = middistance()

            # if distance is more than empty distance then jsut take it tank = empty
            if distance > total_tank_deph:
                distance = total_tank_deph

            tTimestamp  = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.localtime(time.time()))       # timestamp for Influx, down to the second
          
            tWaterLevel = waterheight(distance)                                  # how many cm of water do we have                                           
            tPercentage = filledpercenatge(tWaterLevel)                         # Percentage filled
            tVolume     = watervolume(tPercentage)                               # How many L do we have
            tDistance   = round( distance, 2)

            # select * from "Water-Tank-Levels"
            # select * from "Water-Tank-Levels" where tag ="Council-Tank-Left"
            json_data = {
                "measurement" : measurement,        # select from "< >""
                    "tags": {                       # where tank = "< >"
                        "tank": tag
                    },
                    "time" : tTimestamp,
                    "fields": {
                        "water_level":      tWaterLevel,        # cm of water in tank
                        "fill_percentage":  100*tPercentage,    # based on distance and tank depth, percentage full
                        "water_volume":     tVolume,            # based on percentage and tank capacity
                        "distance":         tDistance,          # distance to water surface
                    }
                }
            

            my_logger.info('{time}, Measurement: {measurement}, Tag: {tag}, H2O Level : {level} cm, Fill Percentage: {percentage}%, Liters in Tank {volume} L '.format(
                time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
                measurement = measurement,
                tag         = tag,
                level       = tWaterLevel,          # cm of water
                percentage  = 100*tPercentage,      # tank fille percentage based on useable capacity
                volume      = tVolume               # water volume in tank
            ))  

            ########################################################################
            # Insert into InfluxDB Database

            insertInflux(influx_client, [json_data])

            # Publish MQTT
            publishMQTT(client, json_data)

            my_logger.debug("")
            json_formatted_str = json.dumps(json_data, indent=2)
            my_logger.info(json_formatted_str)                

            time.sleep(sleep_seconds)

    except Exception as err:

        my_logger.error('{time}, Soemthing went wrong / Error... {err}'.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            err=err
        ))
  
    except KeyboardInterrupt:
        # Reset by pressing CTRL + C

        my_logger.error('{time}, Shutting Down Unexpectedly...'.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
        ))

        sys.stdout.flush()
        sys.exit(-1)

    finally:

        my_logger.info('{time}, Closing InfluxDB Connection... '.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))
        influx_client.close()
        
        my_logger.info('{time}, GPIO Cleanup... '.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))
        GPIO.cleanup()

        # Cleanup
        my_logger.info('{time}, MQTT Disconnect... '.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))
        client.disconnect()  # disconnect

        my_logger.info('{time}, Goodbye... '.format(
            time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ))

# end main 


if __name__ == '__main__':

    my_logger.info("")
    my_logger.info('{time}, Starting... '.format(
        time=str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
    ))

    main()

# end def


