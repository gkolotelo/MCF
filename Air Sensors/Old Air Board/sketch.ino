#define LIGHT_SENSOR A0
#define UV_SENSOR A1
#define O2_SENSOR A2
#define NO2_SENSOR A3
#define CO_SENSOR A4
#define NO2CO_HEATING 4
#define TEMPHUM_SENSOR 2
#define DUST_SENSOR 8
#define DHTTYPE DHT22 
#define ledpin 13//Arduino built-in LED

//imports
#include <Wire.h>
#include "Barometer.h"
#include "DHT.h"

typedef struct {
  String name;
  float value;
  String units;
} sensor;

DHT dht(TEMPHUM_SENSOR,DHTTYPE);
Barometer barometer;
unsigned long duration;
unsigned long starttime;
unsigned long sampletime_ms = 30000; //sampe 30s
unsigned long lowpulseoccupancy = 0;//Lo Pulse Occupancy Time (LPO Time)
float dust_ratio = 0;

char input[20];
char r = ' ';
int i;

sensor light={"Light", 0, "N/A"},
uv={"UV", 0, "N/A"},
o2={"O2", 0, "N/A"},
no2={"NO2", 0, "N/A"},
co={"CO", 0, "N/A"},
co2={"CO2", 0, "N/A"},
temp={"Temperature", 0, "C"},
humidity={"Humidity", 0, "RH"},
pressure={"Pressure", 0, "atm"},
altitude={"Altitude", 0, "m"},
baro_temp={"Barometer Temperature", 0, "C"},
dust_conc={"Dust", 0, "N/A"};
sensor* sensors[] = {&co2, &light, &uv, &o2, &no2, &co, &temp, &humidity, &pressure, &altitude, &baro_temp, &dust_conc};
int number_of_meas = 12;

void makeReadings(){
  o2.value = analogRead(O2_SENSOR);
  o2.value = (o2.value/1024)*5;
  o2.value = (o2.value/201)*1000;
  o2.value = o2.value*2;
  
  light.value = analogRead(LIGHT_SENSOR);
  light.value = (light.value/1024)*5;
  
  long uv_sum = 0;
  for(int i=0;i<1024;i++)
  {  
     uv_sum += analogRead(UV_SENSOR);
     delay(2);
  }
  uv_sum = uv_sum >> 10;
  uv.value = uv_sum*4980.0/1023.0;//UV in mV
  
  temp.value = dht.readTemperature();
  humidity.value = dht.readHumidity();
  
  baro_temp.value = barometer.bmp085GetTemperature(barometer.bmp085ReadUT());
  pressure.value = barometer.bmp085GetPressure(barometer.bmp085ReadUP());//Pressure in Pa
  altitude.value = barometer.calcAltitude(pressure.value);//altitude in m
  pressure.value = pressure.value/101325; //Pressure in atm
  
  no2.value = analogRead(NO2_SENSOR);
  co.value = analogRead(CO_SENSOR);
  
  duration = pulseIn(DUST_SENSOR, LOW);
  lowpulseoccupancy = lowpulseoccupancy+duration;
  if ((millis()-starttime) > sampletime_ms)
  {
    dust_ratio = lowpulseoccupancy/(sampletime_ms*10.0);  // Integer percentage 0=>100
    dust_conc.value = 1.1*pow(dust_ratio,3)-3.8*pow(dust_ratio,2)+520*dust_ratio+0.62; // using spec sheet curve
    dust_conc.value = 100*dust_conc.value;//now in particles per cf
    lowpulseoccupancy = 0;
    starttime = millis();
  }
  
  co2.value = 450*(1+0.03*sin((micros()/720000000)));

}

void setup()
{
  Serial.begin(38400);
  dht.begin();
  barometer.init();
  digitalWrite(NO2CO_HEATING, HIGH);//NO2 CO preheating
  //delay(10000); //turn back on for production!!!
  digitalWrite(NO2CO_HEATING, LOW);
  starttime = millis();//may be able to remove
}

void loop()
{
  i = 0;
  if(Serial.available())
  {
    while(Serial.available() > 0)
    {
      if(i < 19)
      {
        r = Serial.read();
        input[i++] = r;
        input[i] = '\0';
        delay(10);
      }
      else break;
    }
    delay(30);
    Serial.flush();
    delay(30);
    while (Serial.available())
    {
      Serial.read();
    }
    
    switch((int)input[0])
    {
      case 'R':
      case 'r':
      default:
      digitalWrite(ledpin, HIGH);
      input[0] = ' ';
      input[1] = ' ';
      makeReadings();
      for(int j=0; j<number_of_meas; j++)
      {
        //Serial.print(sensors[j]->name);
        //Serial.print(",");
        Serial.print(sensors[j]->value);
        if (j == number_of_meas-1) Serial.println();
        else Serial.print(",");
        //Serial.print(sensors[j]->units);
        //Serial.print(",");
      }
    }
  }
}







