#include "ModbusMaster.h"
#include <SoftwareSerial.h>

uint8_t read_temp[7] = {0xfe,0x44, 0x00, 0x08, 0x02, 0x9f, 0x25};
uint8_t init_meas[8] = {0xfe,0x41, 0x00, 0x60, 0x01, 0x35, 0xe8, 0x53};

SoftwareSerial serial(8,9);
String readString = "";
void setup()
{
  Serial.begin(9600);
  serial.begin(9600);

}

void loop()
{
  serial.write(init_meas,sizeof(init_meas));
  delay(1000);
  while (serial.available()) {
    delay(20);
    char c = serial.read();
    readString += c;
  }
  if(readString != )
  Serial.print("Init reading: ");
  Serial.println(readString);
  readString = "";
  
  delay(15000);
  
  serial.write(read_temp,sizeof(read_temp));
  delay(1000);
  while (serial.available()) {
    delay(20);
    char c = serial.read();
    readString += c;
  }
  if ((uint8_t)readString[0] == 254 && (uint8_t)readString[1] == 68 && (uint8_t)readString[2] == 2)
  {
    Serial.println("Data read: ");
    for(int i=3;i<readString.length()-2;i++)
    {
      Serial.print((uint8_t)(readString[i]));
      Serial.print(",");
    }
    Serial.println();
    for(int i=3;i<readString.length()-2;i++)
    {
      Serial.print(readString[i]);
      Serial.print(",");
    }
    Serial.println();
    Serial.print("CO2: ");
    Serial.println((uint8_t)(readString[3]*16*16+(uint8_t)(readString[4])));
    
  }

    readString = "";

}
