String vers = "Air Sensor Board V0.3.1 12/21/2014";
//Pin definitions:
// LIGHT_UV_IR_SENSOR I2C
#define O2_SENSOR A0
#define CO2_SENSOR_RX 8
#define CO2_SENSOR_TX 9
#define TEMP_PROBE 6
#define TEMPHUM_SENSOR 4
#define DUST_SENSOR 2
#define DHTTYPE DHT22 
#define ledpin 13//Arduino built-in LED
#define LED 5
#define NUMPIXELS      16

//includes
#include <Wire.h>
#include "Adafruit_NeoPixel.h"
#include "Adafruit_SI1145.h"
#include "DHT.h"
#include "OneWire.h"
#include <math.h>
#include <SoftwareSerial.h>

//Sensor data type
typedef struct {
  String name;
  float value;
  String units;
} sensor;

//Instantiations
//DHT
DHT dht(TEMPHUM_SENSOR,DHTTYPE);
//Dust
unsigned long duration;
unsigned long starttime;
unsigned long sampletime_ms = 30000; //sampe 30s
unsigned long lowpulseoccupancy = 0;//Lo Pulse Occupancy Time (LPO Time)
float dust_ratio = 0;
//Temperature probe
OneWire temp_probe(TEMP_PROBE);
byte temp_probe_addr[8];
byte temp_probe_data[12];
//Light UV IR sensor
Adafruit_SI1145 uv_sensor = Adafruit_SI1145();
//LED Strip
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUMPIXELS, LED, NEO_GRB + NEO_KHZ800);
//COZIR CO2 sensor
SoftwareSerial serial(CO2_SENSOR_RX,CO2_SENSOR_TX);
String readString = "";
char buff[10];

//Global variables, used for serial commands 
char input[20];
char r = ' ';
int i;

//Initialization of sensor structs
sensor light={"Light", 0, "N/A"},
uv={"UV", 0, "Index"},
ir={"IR", 0, "N/A"},
o2={"O2", 0, "N/A"},
co2={"CO2", 0, "ppm"},
temp={"Air Temperature", 0, "C"},
water_temp={"Water Temperature", 0, "C"},
co2_temp={"Air Temperature CO2", 0, "C"},
humidity={"Humidity", 0, "RH"},
co2_humidity={"Humidity CO2", 0, "RH"},
dust_conc={"Dust", 0, "N/A"};
sensor* sensors[] = {&co2, &light, &uv, &ir, &o2, &water_temp, &temp, &co2_temp, &humidity, &co2_humidity, &dust_conc};
int number_of_meas = sizeof(sensors) / sizeof(sensor*);

//Initial Thresholds:
//thresholds: LT,HT,KT,LWT,HWT,KWT,LH,HH,KH,LCO2,HCO2,KCO2,KErr
//Format breakdouwn: Set Low_air_Temp,High_air_Temp,K_air_temp,Low_Water_temp,High_Water_Temp,K_water_temp,Low_Humidity,High_Humidity,K_humidity,Low_CO2,High_CO2,K_CO2,K_Error_Multiplier
float thresholds[] = {20, 25, 20, 20, 25, 200, 40, 60, 900, 400, 600, 300, 100};

//Methods
void makeReadings();
void setLEDSmooth();


void setup()
{
  //Begin USB Serial port
  Serial.begin(9600);
  //Begin DHT Temp Humidity sensor
  dht.begin();
  //Initialize 'starttime' var for Dust sensor
  starttime = millis();
  //Begin Light, UV, IR sensor
  uv_sensor.begin();
  //Find temperature probe OneWire address, and select it
  temp_probe.search(temp_probe_addr);
  temp_probe.reset();
  temp_probe.select(temp_probe_addr);
  //Begin LED strip
  pixels.begin();
  //Begin SoftwareSerial for COZIR CO2 sensor
  serial.begin(9600);
  serial.println("K 2");
  serial.flush();
  
  delay(1000);
}

void loop()
{
  readString = "";
  while(Serial.available())
  {
    readString += (char)Serial.read();
    delay(10);
  }
  Serial.flush();
  delay(20);
  if(readString.indexOf('\r') != -1)//Else: do nothing, Invalid data.
  {
    switch(readString.charAt(0))
    {
      case 'R':
      case 'r':
        makeReadings();
        setLEDSmooth();
        for(int j=0; j<number_of_meas; j++)
        {
          //Prints sensor data in the following order:
          //co2, light, uv, ir, o2, water_temp, temp, co2_temp, humidity, co2_humidity, dust_conc
          Serial.print(sensors[j]->name);
          Serial.print(sensors[j]->value);
          if (j == number_of_meas-1) Serial.println();
          else Serial.print(",");
        }
        break;
        
      case 'I':
      case 'i':
        //Print information about the board
        Serial.println(vers);
        break;
        
      case 'S':
      case 's':
        //Set LED thresholds
        //Format: S,LT,HT,LWT,HWT,LH,HH,LCO2,HCO2,K\r
        //Format breakdouwn: Set Low_air_Temp,High_air_Temp,Low_Water_temp,High_Water_Temp,Low_Humidity,High_Humidity,Low_CO2,High_CO2,Error_Proportionality_Constant
        readString += ','; //Add a comma so the loop below can be made simpler
        int i = readString.indexOf(',');
        for(int j = 0; j < sizeof(thresholds)/sizeof(float); j++)
        {
          readString = readString.substring(i+1);
          i = readString.indexOf(',');
          thresholds[j] = readString.substring(0,i).toInt();
        }
        break;
    }
  }
}


void makeReadings(){
  digitalWrite(ledpin, HIGH); //Turn on status LED

  //O2 Sensor
  o2.value = analogRead(O2_SENSOR);
  o2.value = (o2.value/1024)*5;
  o2.value = (o2.value/201)*1000;
  o2.value = o2.value*2;
  //DHT Temp and Humidity sensor
  temp.value = dht.readTemperature();
  humidity.value = dht.readHumidity();
  //Dust
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
  //Light, UV, IR
  light.value = uv_sensor.readVisible();
  ir.value = uv_sensor.readIR();
  uv.value = uv_sensor.readUV()/100;
  //Temperature probe
  temp_probe.reset();
  temp_probe.select(temp_probe_addr);   
  temp_probe.write(0x44, 1);
  delay(1000);
  temp_probe.reset();
  temp_probe.select(temp_probe_addr); 
  temp_probe.write(0xBE);
  for (int i = 0; i < 9; i++) {
    temp_probe_data[i] = temp_probe.read();
  }
  int16_t raw = (temp_probe_data[1] << 8) | temp_probe_data[0];
  water_temp.value = (float)raw / 16.0;
  //COZIR CO2 sensor
  //CO2
  serial.flush();
  delay(50);
  serial.println("Z");
  delay(50);
  readString = "";
  while(serial.available())
  {
    readString += (char)serial.read();
  }
  readString = readString.substring(readString.indexOf(' ',1)+1);
  co2.value = readString.toInt();
  //Humidity
  serial.flush();
  delay(50);
  serial.println("H");
  delay(50);
  readString = "";
  while(serial.available())
  {
    readString += (char)serial.read();
  }
  readString = readString.substring(readString.indexOf(' ',1)+1);
  readString.toCharArray(buff, readString.length());
  co2_humidity.value = atof(buff)/10; // Divide by 10 to get the %RH
  //Temperature
  serial.flush();
  delay(50);
  serial.println("T");
  delay(50);
  readString = "";
  while(serial.available())
  {
    readString += (char)serial.read();
  }
  readString = readString.substring(readString.indexOf(' ',1)+1);
  readString.toCharArray(buff, readString.length());
  co2_temp.value = (atof(buff)-1000)/10; //Subtract 1000 and divide by 10 to get the temperature in ⁰C
  
  digitalWrite(ledpin, LOW);//Turn off status LED
}

float error(float reading, float L, float H, float a)
{
  //e -> Error
  //L -> Low Threshold
  //H -> High Threshold
  //a -> Error Slew Ratio (between 0 and 1, the higher the faster the LED colors change)
  //a makes the logit function == 1 at 0.5 +- a/2
  a = a/1000;
  float err = reading * a/(H-L) - L*a/(H - L) + (0.5 - a/2);
  if(err <= 0.001) err = 0.001;
  if(err >= 0.999) err = 0.999;
  Serial.println(err);
  float correction = log( (a/2 + 0.5) / (1 - (a/2 + 0.5)) );
  err = log(err/(1-err))/correction/5;
  if(err <= -1) return -1;
  if(err >= 1) return 1;
  return err;
}

void setLEDSmooth()
{
  //thresholds: LT,HT,KT,LWT,HWT,KWT,LH,HH,KH,LCO2,HCO2,KCO2,K
  //thresholds[0] -> LT
  //thresholds[1] -> HT
  //thresholds[2] -> KT
  //thresholds[3] -> LWT
  //thresholds[4] -> HWT
  //thresholds[5] -> KWT
  //thresholds[6] -> LH
  //thresholds[7] -> HH
  //thresholds[8] -> KH
  //thresholds[9] -> LCO2
  //thresholds[10]-> HCO2
  //thresholds[11]-> KCO2
  //thresholds[12]-> K
//Old:
//  float r = 0, g = 0, b = 0;
//  float err_T = ((((thresholds[0]+thresholds[1])/2) - (temp.value > thresholds[1] ? thresholds[1] : (temp.value < thresholds[0] ? thresholds[0] : temp.value)))/(thresholds[1]-thresholds[0]))*thresholds[2];
//  float err_WT = ((((thresholds[3]+thresholds[4])/2) - (water_temp.value > thresholds[4] ? thresholds[4] : (water_temp.value < thresholds[3] ? thresholds[3] : water_temp.value)))/(thresholds[4]-thresholds[3]))*thresholds[5];
//  float err_H = ((((thresholds[6]+thresholds[7])/2) - (humidity.value > thresholds[7] ? thresholds[7] : (humidity.value < thresholds[6] ? thresholds[6] : humidity.value)))/(thresholds[7]-thresholds[6]))*thresholds[8];
//  float err_CO2 = ((((thresholds[9]+thresholds[10])/2) - (co2.value > thresholds[10] ? thresholds[10] : (co2.value < thresholds[9] ? thresholds[9] : co2.value)))/(thresholds[10]-thresholds[9]))*thresholds[11];
//  Serial.print("T ");
//  Serial.println(err_T);
//  Serial.print("WT ");
//  Serial.println(err_WT);
//  Serial.print("H ");
//  Serial.println(err_H);
//  Serial.print("CO2 ");
//  Serial.println(err_CO2);
//  float max_err = max(fabs(err_T), max(fabs(err_H), max(fabs(err_CO2), fabs(err_WT))));
//  float min_err = min(err_T, min(err_H, min(err_CO2, err_WT)));
//  Serial.print("Max ");
//  Serial.println(max_err);
//  Serial.print("Min ");
//  Serial.println(min_err);
//  float err;
//  if (max_err == fabs(min_err))//error is negative
//    err = - min_err*min_err*min_err*thresholds[12];
//  else err = - max_err*max_err*max_err*thresholds[12];
//  Serial.print("err ");
//  Serial.println(err);
//  Serial.print("Error ");
//  Serial.println(error(err));
//New:
  float r = 0, g = 0, b = 0;
  float err_WT = error(water_temp.value, thresholds[3], thresholds[4], thresholds[5]);
  float err_T = error(temp.value, thresholds[0], thresholds[1], thresholds[2]);
  float err_H = error(humidity.value, thresholds[6], thresholds[7], thresholds[8]);
  float err_CO2 = error(co2.value, thresholds[9], thresholds[10], thresholds[11]);
  float max_err = max(fabs(err_T), max(fabs(err_H), max(fabs(err_CO2), fabs(err_WT))));
  float min_err = min(err_T, min(err_H, min(err_CO2, err_WT)));
  float err;
  if (max_err == fabs(min_err))//error is negative
    err = min_err*(thresholds[12]/100);
  else err = max_err*(thresholds[12]/100);
  //Set LEDs:
  if(err < 0)
  {
    b = 255*(-err);
    g = 255*(1+err);
  }
  else
  {
    g = 255*(1-err);
    r = 255*(err);
  }
  pixels.setBrightness(80);
  uint32_t c = pixels.getPixelColor(1);
  float o_r = (float)(uint8_t)(c >> 16),
  o_g = (float)(uint8_t)(c >>  8),
  o_b = (float)(uint8_t)c,
  dr = (r - o_r)/128,
  dg = (g - o_g)/128,
  db = (b - o_b)/128;
  for(int j = 0; j < 128; j++)
  {
    o_r += dr;
    o_g += dg;
    o_b += db;
    for(int i=0;i<NUMPIXELS;i++){
      pixels.setPixelColor(i, pixels.Color((int)o_r,(int)o_g,(int)o_b));
      pixels.show();
    }
  }
}
