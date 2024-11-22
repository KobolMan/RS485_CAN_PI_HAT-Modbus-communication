#include <SoftwareSerial.h>
#include "modbus_crc.h"

SoftwareSerial RS485(2, 8); // RX, TX
int RS485_E = 7;
unsigned char  cmd[8] = {0x01,0x04,0x00,0x00,0x00,0x08,0xF1,0xCC}; 
unsigned char buf[100];
unsigned int  crc;
unsigned int  input[8];
unsigned char i,j;

void setup()  
{
  Serial.begin(115200);
  Serial.println("*** Modbus RTU Analog Input Test Program ***\r\n");

  RS485.begin(9600);
  pinMode(RS485_E,OUTPUT);
}

void loop() // run over and over
{   
    digitalWrite(RS485_E,HIGH);   //send
    for(i=0;i<8;i++){
      RS485.write(cmd[i]);
    }
    digitalWrite(RS485_E,LOW);   //RECEIVE
    delay(2);
    j=0;
    while (RS485.available() > 0)
    {
      buf[j]= char(RS485.read());  
      delay(2);
      j++;
    }
    if(j == 21){
      crc = ModbusCRC((unsigned char  *)buf,19);
      if((buf[19] == (crc & 0xFF)) && (buf[20] == (crc >> 8)))
      {
        for(i=0;i<8;i++){
          input[i] = (buf[3+i*2] * 0x100) + buf[4+i*2];
          Serial.print(input[i], DEC);
          Serial.print(" ");
        }
        Serial.println("");
      }else{
        Serial.println("CRC ERR!!");
      }
    }else{
      Serial.println("Length ERR!!");
    }
    delay(1000);
}
