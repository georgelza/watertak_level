#%%Sensor
#Libraries
import RPi.GPIO as GPIO
import time
import statistics
 
#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)
 
#set GPIO Pins
GPIO_TRIGGER = 18
GPIO_ECHO = 24
 
#set GPIO direction (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
 
def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)
 
    # set Trigger after 0.01ms to LOW
    time.sleep(0.00005)
    GPIO.output(GPIO_TRIGGER, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()
        # wait for real bounce
        time.sleep(0.0005)
 
    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
 
    return distance

def middis():
    runs=[]
    for i in range(11):
        runs.append(distance())
        time.sleep(1)
    #print(runs)
    midrun = statistics.median(runs)
    return midrun

def cisternlevel(dist_to_water):
    #dist = middis()
    cisterndepth = 270 #set cistern total depth
    bufferheight = 25 #set height of sensor above max waterline + safety buffer
    cisternlevel = 100 * (cisterndepth + bufferheight - dist_to_water) / cisterndepth
    return cisternlevel
    
    
#%% MQTT
import paho.mqtt.client as mqtt
def bigmqtt():
    def on_connect(client, userdata, flags, rc):
        if rc==0:
            cisternclient.connected_flag = True
            print("connected ok returned code=",rc)
        else:
            cisternclient.bad_connection_flag=True
            print("bad connection returned code=",rc)
        
        
    def on_publish(client,userdata,result):
            print("data published \n")
            pass
    
    def on_disconnect(client,userdata,rc):
        logging.info("disconnected reason " +str(rc))
        cisternclient.connected_flag = False
        cisternclient.disconnect_flag = True

    # configure mqtt connection

    broker = "192.168.xx.xx"
    port = xxx
    username = "xxx"
    password = "xxx"
    mqtt.Client.connected_flag=False
    mqtt.Client.bad_connection_flag=False
    cisternclient=mqtt.Client("cistern1")
    cisternclient.username_pw_set(username, password)
    cisternclient.connected_flag = False
    cisternclient.on_connect = on_connect
    cisternclient.on_publish = on_publish
    cisternclient.will_set("borgo/cistern/health",payload="Disconnected",qos=0,retain=False)

    cisternclient.loop_start()
    try:
        cisternclient.connect(broker, port, keepalive=10)
        while not cisternclient.connected_flag and not cisternclient.bad_connection_flag:
            print("in wait loop")
            time.sleep(1)
        if cisternclient.bad_connection_flag:
            cisternclient.loop_stop()
            exit() #exit where?
        print("in Main loop")
        if __name__ == '__main__':
            try:
                while True:
                    dist = middis()
                    percentlevel=cisternlevel(dist)
                    print ("distance to top = %.1f cm" % dist)
                    print ("cistern level = %.1f percent" % percentlevel)
                    cisternclient.publish("borgo/cistern/level",payload=percentlevel,qos=0,retain=True)
                    cisternclient.publish("borgo/cistern/dist",payload=dist,qos=0,retain=True)
                    cisternclient.publish("borgo/cistern/health",payload="Connected",qos=0,retain=True)
                    time.sleep(10)
            except:
                print("smth broke")
                exit(1)
    except:
        print("main loop connection failed")
        exit(1)
    cisternclient.loop_stop()
    cisternclient.disconnect()
    

if __name__ == '__main__':
    try:
        while True:
            print("alors on danse")
            bigmqtt()
            time.sleep(10)
        # Reset by pressing CTRL + C
    except KeyboardInterrupt:
        print("Measurement stopped by User")
        GPIO.cleanup()