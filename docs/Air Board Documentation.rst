Air Board Documentation
=======================

The Air board is a collection of air quality sensors installed in an acrylic box with an Arduino as the interface between the individual sensors and a computer via a UBS to serial connection.

Air quality sensors:
--------------------
	Temperature and Humidity sensor (DHT22)
	CO2 sensor (COZIR)
	Light,UV,IR sensor (Adafruit Digital UV Sensor)
	Dust (Grove Dust Sensor)
	O2 sensor (Grove O2 Gas Sensor)

Water quality sensor:
---------------------
	Water Temperature Probe (OneWire Temperature Probe)

Status Feedback:
----------------
	2 LED strips (Adafruit NeoPixel 8 LED Stick)


The Status feedback lights make it easy to determine the air/water quality status of the system the Air Board is in. If the measurements are near to their low thresholds the LEDs will display a blueish color; if the measurements are near high thresholds the LEDs will display a reddish color, and if the values are within the thresholds the LEDs will light up green, indicating tht the board is in an acceptable environment. The thresholds have standard values built into the code, however they can be redefined through a command.

Error calculation is given by:

	maximum of the errors where each error is given by error(reading,, Low_Threshold, High_Threshold, Slew_Rate)

	The error function is an inverse sigmoid (logit) function, where the slew rate variable determines how fast the error diverges from zero when near the thresholds.

The LEDs color are set based on this error.

The Air Board's Arduino is programmed to work with the SerialSensor library, and responds to the following serial commands:

Serial Commands:
----------------

	``r\r``: Returns the measurement values after 5 seconds. After each reading the LED strip color is set according to the thresholds.
		The default order of the measurements is:
			“CO2, Light, UV, IR, O2, Water_Temperature, Temperature, CO2_Temperature, Humidity, CO2_Humidity, Dust”
		With the following units:
			“ppm, N/A, Index, N/A, percent, C, C, C, RH, RH, N/A”

	``i\r``: Returns information about the Air Board.

	``s,LT,HT,SRT,LWT,HWT,SRWT,LH,HH,SRH,LCO2,HCO2,SRCO2,KErr%\r``: Sets the threshold values, where:

			LT:   	Low Air Temperature Threshold
			HT:   	High Air Temperature Threshold
			SRT:  	Slew Rate of Air Temperature error function
			LWT:  	Low Water Temperature Threshold
			HWT:  	High Water Temperature Threshold
			SRWT: 	Slew Rate of Water Temperature error function
			LH:   	Low Humidity Threshold
			HH:   	High Humidity Threshold
			SRH:    Slew Rate of Humidity error function
			LCO2: 	Low CO2 Threshold
			HCO2: 	High CO2 Threshold
			SRCO2:	Slew Rate of CO2 error function
			KErr%:	Constant that multiplies final error

