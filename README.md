# Watertank level

Python code to read Ultrasonic sensor (HC-SR04), measuring water level (distance) in a tank,

Converting the distance into a percentage of the tank filled.

Converting the percentage into a water volume based on tank capacity.

Inserting all values into a InfluxDB (hosted on Oblix), to be visualized via Grafana dashboard.

Publishing values onto a mqtt topic, to be visualized in Home Assistant
