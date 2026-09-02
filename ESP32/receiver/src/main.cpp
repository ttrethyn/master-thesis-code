#include <Arduino.h>

#include "nvs_flash.h"

#include "esp_mac.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_now.h"
#include "FS.h"
#include "SD.h"
#include "SPI.h"

#include <Adafruit_Sensor.h>
#include <RTClib.h>
#include <Wire.h>

RTC_DS1307 rtc;

// WiFi parameters
#define CONFIG_LESS_INTERFERENCE_CHANNEL    11
#define CONFIG_SEND_FREQUENCY               100           // in hz

// string length parameters
#define CSI_SIZE                            1645
#define TIME_SIZE                           24
#define FILENAME_SIZE                       26

// startup leds
#define WIFI_PIN    D0
#define SD_PIN      D2

// mac addresses
static const uint8_t MAC_ADDR_SEND_1[] = {0x1a, 0x00, 0x01, 0x00, 0x00, 0x00};
static const uint8_t MAC_ADDR_SEND_2[] = {0x1a, 0x00, 0x02, 0x00, 0x00, 0x00};
static const uint8_t MAC_ADDR_SEND_3[] = {0x1a, 0x00, 0x03, 0x00, 0x00, 0x00};
static const uint8_t MAC_ADDR_RECV[] = {0x1a, 0x03, 0x00, 0x00, 0x00, 0x00};

// time management
unsigned long new_time = 0;
unsigned long old_time = 0;
uint8_t new_second = 0;
uint8_t old_second = 0;
DateTime sent_time;
DateTime waiting_time;

// csi storage
char csi_data0[40][CSI_SIZE];
char csi_data1[40][CSI_SIZE];
int csi_idx = 0;
bool csi_switch = true;
char csi_name[20];

// initialisation variables
bool wifi_good;
bool rtc_good;
bool sd_good;

// whether or not to write to sd card
bool write_flag;

// function declarations
void generate_timestamp(char*, DateTime*, bool, unsigned long);
bool report_esp_error(esp_err_t);
bool rtc_setup();
bool sd_setup();
bool wifi_setup();
static void wifi_csi_rx_cb(void*, wifi_csi_info_t*);

void setup() 
{
  Serial.begin(115200);

  // initialise the pins for the leds
  pinMode(WIFI_PIN, OUTPUT);
  pinMode(SD_PIN, OUTPUT);

  // run all setup functions, where appropriate set leds to high to indicate success
  sd_good = sd_setup();
  if(sd_good) digitalWrite(SD_PIN, HIGH);
  rtc_good = rtc_setup();
  sent_time = rtc.now();
  waiting_time = sent_time;
  wifi_good = wifi_setup();
  if(wifi_good) digitalWrite(WIFI_PIN, HIGH);
}

void loop() 
{
  // if it is time to write and the sd was initialised successfully
  if(write_flag && sd_good)
  {
    // indicate that we are writing, set the flag to false, and get the current array of csi data
    Serial.println("Time to write");
    write_flag = false;
    bool csi_switch_local = csi_switch;
    sent_time = rtc.now();
    waiting_time = sent_time;

    // initialise strings for writing
    char file[FILENAME_SIZE];
    char timestamp[TIME_SIZE];

    // fill them with the time and the file name
    DateTime now = rtc.now();
    generate_timestamp(timestamp, &now, true, 0);
    sprintf(file, "/image%s.jpg", timestamp);

    Serial.printf("Writing filename: %s\n", file);

    // open the csi csv and report on success/failure
    File csi_file = SD.open(csi_name, FILE_APPEND);
    if(!csi_file)
    {
      Serial.println("Failed to open csi file for writing");
    }
    else
    {
      Serial.println("Opened csi file");
    }

    // write csi to csv
    Serial.println("Writing csi csv");
    if (csi_switch_local)
    {
      for(int i=0;i<40;i++)
      {
        csi_file.println(csi_data1[i]);
      }
    }
    else
    {
      for(int i=0;i<40;i++)
      {
        csi_file.println(csi_data0[i]);
      }
    }

    csi_file.close();
    Serial.println("csi csv saved");
  }
  else
  {
    waiting_time = rtc.now();
    if (waiting_time.unixtime() - sent_time.unixtime() >= 120)
    {
      esp_restart();
    }
  }
}

void generate_timestamp(char* timestamp, DateTime* now, bool img, unsigned long milli = 0)
{
  // generate a timestamp in the format yyyyMMddmmss for in an image file name, or in the format yyyy:MM:dd:mm:ss:millis for in a csv
  if(img)
  {
    if(now->month() >= 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d", now->year(), now->month(), now->day(), now->hour(), now->minute(), now->second());                           //00000
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d", now->year(), now->month(), now->day(), now->hour(), now->minute(), 0, now->second());                      //00001
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d", now->year(), now->month(), now->day(), now->hour(), 0, now->minute(), 0, now->second());                 //00011
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d", now->year(), now->month(), now->day(), now->hour(), 0, now->minute(), now->second());                      //00010
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() < 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d", now->year(), now->month(), now->day(), 0, now->hour(), 0, now->minute(), now->second());                 //00110
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() < 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d", now->year(), now->month(), now->day(), 0, now->hour(), 0, now->minute(), 0, now->second());            //00111
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() < 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d", now->year(), now->month(), now->day(), 0, now->hour(), now->minute(), 0, now->second());                 //00101
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() < 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d", now->year(), now->month(), now->day(), 0, now->hour(), now->minute(), now->second());                      //00100
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() < 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d", now->year(), now->month(), 0, now->day(), 0, now->hour(), now->minute(), now->second());                 //01100
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() < 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d", now->year(), now->month(), 0, now->day(), 0, now->hour(), now->minute(), 0, now->second());            //01101
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() < 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d%d", now->year(), now->month(), 0, now->day(), 0, now->hour(), 0, now->minute(), 0, now->second());       //01111
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() < 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d", now->year(), now->month(), 0, now->day(), 0, now->hour(), 0, now->minute(), now->second());            //01110
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() >= 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d", now->year(), now->month(), 0, now->day(), now->hour(), 0, now->minute(), now->second());                 //01010
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() >= 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d", now->year(), now->month(), 0, now->day(), now->hour(), 0, now->minute(), 0, now->second());            //01011
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d", now->year(), now->month(), 0, now->day(), now->hour(), now->minute(), 0, now->second());                 //01001
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d", now->year(), now->month(), 0, now->day(), now->hour(), now->minute(), now->second());                      //01000
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), 0, now->day(), now->hour(), now->minute(), now->second());                 //11000
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), 0, now->day(), now->hour(), now->minute(), 0, now->second());            //11001
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() >= 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), 0, now->day(), now->hour(), 0, now->minute(), 0, now->second());       //11011
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() >= 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), 0, now->day(), now->hour(), 0, now->minute(), now->second());            //11010
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() < 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), 0, now->day(), 0, now->hour(), 0, now->minute(), now->second());       //11110
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() < 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), 0, now->day(), 0, now->hour(), 0, now->minute(), 0, now->second());  //11111
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() < 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), 0, now->day(), 0, now->hour(), now->minute(), 0, now->second());       //11101
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() < 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), 0, now->day(), 0, now->hour(), now->minute(), now->second());            //11100
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() < 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), now->day(), 0, now->hour(), now->minute(), now->second());                 //10100
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() < 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), now->day(), 0, now->hour(), now->minute(), 0, now->second());            //10101
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() < 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), now->day(), 0, now->hour(), 0, now->minute(), 0, now->second());       //10111
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() < 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), now->day(), 0, now->hour(), 0, now->minute(), now->second());            //10110
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), now->day(), now->hour(), 0, now->minute(), now->second());                 //10010
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), now->day(), now->hour(), 0, now->minute(), 0, now->second());            //10011
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d%d", now->year(), 0, now->month(), now->day(), now->hour(), now->minute(), 0, now->second());                 //10001
    }
    else
    {
      sprintf(timestamp, "%d%d%d%d%d%d%d", now->year(), 0, now->month(), now->day(), now->hour(), now->minute(), now->second());                      //10000
    }
  }
  else
  {
    if(now->month() >= 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d:%d:%d:%d:%d:%lu", now->year(), now->month(), now->day(), now->hour(), now->minute(), now->second(), milli);                           //00000
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d:%d:%d:%d:%d%d:%lu", now->year(), now->month(), now->day(), now->hour(), now->minute(), 0, now->second(), milli);                      //00001
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d:%d:%d:%d%d:%d%d:%lu", now->year(), now->month(), now->day(), now->hour(), 0, now->minute(), 0, now->second(), milli);                 //00011
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d:%d:%d:%d%d:%d:%lu", now->year(), now->month(), now->day(), now->hour(), 0, now->minute(), now->second(), milli);                      //00010
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() < 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d:%d:%d%d:%d%d:%d:%lu", now->year(), now->month(), now->day(), 0, now->hour(), 0, now->minute(), now->second(), milli);                 //00110
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() < 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d:%d:%d%d:%d%d:%d%d:%lu", now->year(), now->month(), now->day(), 0, now->hour(), 0, now->minute(), 0, now->second(), milli);            //00111
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() < 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d:%d:%d%d:%d:%d%d:%lu", now->year(), now->month(), now->day(), 0, now->hour(), now->minute(), 0, now->second(), milli);                 //00101
    }
    else if(now->month() >= 10 && now->day() >= 10 && now->hour() < 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d:%d:%d%d:%d:%d:%lu", now->year(), now->month(), now->day(), 0, now->hour(), now->minute(), now->second(), milli);                      //00100
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() < 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d:%d%d:%d%d:%d:%d:%lu", now->year(), now->month(), 0, now->day(), 0, now->hour(), now->minute(), now->second(), milli);                 //01100
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() < 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d:%d%d:%d%d:%d:%d%d:%lu", now->year(), now->month(), 0, now->day(), 0, now->hour(), now->minute(), 0, now->second(), milli);            //01101
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() < 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d:%d%d:%d%d:%d%d:%d%d:%lu", now->year(), now->month(), 0, now->day(), 0, now->hour(), 0, now->minute(), 0, now->second(), milli);       //01111
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() < 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d:%d%d:%d%d:%d%d:%d:%lu", now->year(), now->month(), 0, now->day(), 0, now->hour(), 0, now->minute(), now->second(), milli);            //01110
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() >= 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d:%d%d:%d:%d%d:%d:%lu", now->year(), now->month(), 0, now->day(), now->hour(), 0, now->minute(), now->second(), milli);                 //01010
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() >= 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d:%d%d:%d:%d%d:%d%d:%lu", now->year(), now->month(), 0, now->day(), now->hour(), 0, now->minute(), 0, now->second(), milli);            //01011
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d:%d%d:%d:%d:%d%d:%lu", now->year(), now->month(), 0, now->day(), now->hour(), now->minute(), 0, now->second(), milli);                 //01001
    }
    else if(now->month() >= 10 && now->day() < 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d:%d%d:%d:%d:%d:%lu", now->year(), now->month(), 0, now->day(), now->hour(), now->minute(), now->second(), milli);                      //01000
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d%d:%d%d:%d:%d:%d:%lu", now->year(), 0, now->month(), 0, now->day(), now->hour(), now->minute(), now->second(), milli);                 //11000
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d%d:%d%d:%d:%d:%d%d:%lu", now->year(), 0, now->month(), 0, now->day(), now->hour(), now->minute(), 0, now->second(), milli);            //11001
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() >= 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d%d:%d%d:%d:%d%d:%d%d:%lu", now->year(), 0, now->month(), 0, now->day(), now->hour(), 0, now->minute(), 0, now->second(), milli);       //11011
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() >= 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d%d:%d%d:%d:%d%d:%d:%lu", now->year(), 0, now->month(), 0, now->day(), now->hour(), 0, now->minute(), now->second(), milli);            //11010
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() < 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d%d:%d%d:%d%d:%d%d:%d:%lu", now->year(), 0, now->month(), 0, now->day(), 0, now->hour(), 0, now->minute(), now->second(), milli);       //11110
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() < 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d%d:%d%d:%d%d:%d%d:%d%d:%lu", now->year(), 0, now->month(), 0, now->day(), 0, now->hour(), 0, now->minute(), 0, now->second(), milli);  //11111
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() < 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d%d:%d%d:%d%d:%d:%d%d:%lu", now->year(), 0, now->month(), 0, now->day(), 0, now->hour(), now->minute(), 0, now->second(), milli);       //11101
    }
    else if(now->month() < 10 && now->day() < 10 && now->hour() < 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d%d:%d%d:%d%d:%d:%d:%lu", now->year(), 0, now->month(), 0, now->day(), 0, now->hour(), now->minute(), now->second(), milli);            //11100
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() < 10 && now->minute() >= 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d%d:%d:%d%d:%d:%d:%lu", now->year(), 0, now->month(), now->day(), 0, now->hour(), now->minute(), now->second(), milli);                 //10100
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() < 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d%d:%d:%d%d:%d:%d%d:%lu", now->year(), 0, now->month(), now->day(), 0, now->hour(), now->minute(), 0, now->second(), milli);            //10101
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() < 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d%d:%d:%d%d:%d%d:%d%d:%lu", now->year(), 0, now->month(), now->day(), 0, now->hour(), 0, now->minute(), 0, now->second(), milli);       //10111
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() < 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d%d:%d:%d%d:%d%d:%d:%lu", now->year(), 0, now->month(), now->day(), 0, now->hour(), 0, now->minute(), now->second(), milli);            //10110
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() < 10 && now->second() >= 10)
    {
      sprintf(timestamp, "%d:%d%d:%d:%d:%d%d:%d:%lu", now->year(), 0, now->month(), now->day(), now->hour(), 0, now->minute(), now->second(), milli);                 //10010
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() < 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d%d:%d:%d:%d%d:%d%d:%lu", now->year(), 0, now->month(), now->day(), now->hour(), 0, now->minute(), 0, now->second(), milli);            //10011
    }
    else if(now->month() < 10 && now->day() >= 10 && now->hour() >= 10 && now->minute() >= 10 && now->second() < 10)
    {
      sprintf(timestamp, "%d:%d%d:%d:%d:%d:%d%d:%lu", now->year(), 0, now->month(), now->day(), now->hour(), now->minute(), 0, now->second(), milli);                 //10001
    }
    else
    {
      sprintf(timestamp, "%d:%d%d:%d:%d:%d:%d:%lu", now->year(), 0, now->month(), now->day(), now->hour(), now->minute(), now->second(), milli);                      //10000
    }
  }
}

bool report_esp_error(esp_err_t err)
{
  // report on an esp error code in a human readable format. a wrapper for esp_err_to_name
  if(err == ESP_OK)
  {
    return false;
  }
  else
  {
    Serial.printf("Error: %s\n", esp_err_to_name(err));
    return true;
  }
}

bool rtc_setup()
{
  // initialise RTC and report
  if (!rtc.begin()) 
  {
    Serial.println("Failed to find RTC");
    return false;
  }
  Serial.println("RTC Found!");

  // if starting a new measurement set, set date and time to compile time
  if(!SD.exists("/csi_data0.csv"))
  {
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }
  
  // set up the millisecond counter
  old_time = millis();
  DateTime now = rtc.now();
  old_second = now.second();
  return true;
}

bool sd_setup()
{
  // initialize SD card and report
  if(!SD.begin(21))
  {
    Serial.println("Card mount failed");
    return false;
  }
  Serial.println("Card mount succeeded!");

  // get card type
  uint8_t cardType = SD.cardType();

  // determine if the type of SD card is available
  if(cardType == CARD_NONE)
  {
    Serial.println("No SD card attached");
    return false;
  }

  // report on card type
  Serial.print("SD Card Type: ");
  if(cardType == CARD_MMC)
  {
    Serial.println("MMC");
  } 
  else if(cardType == CARD_SD)
  {
    Serial.println("SDSC");
  } 
  else if(cardType == CARD_SDHC)
  {
    Serial.println("SDHC");
  } 
  else 
  {
    Serial.println("UNKNOWN");
  }

  // make a new csv and generate its header
  int csi_num = 0;
  sprintf(csi_name, "/csi_data%i.csv", csi_num);
  while(SD.exists(csi_name))
  {
    csi_num++;
    memset(csi_name, '\0', 20);
    sprintf(csi_name, "/csi_data%i.csv", csi_num);
  } 

  File csi_file = SD.open(csi_name, FILE_WRITE);
  csi_file.println("type,role,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,not_sounding,aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,channel,secondary_channel,local_timestamp,ant,sig_len,rx_state,real_time_set,real_timestamp,len,CSI_DATA");
  csi_file.close();

  return true;
}

bool wifi_setup()
{
  // NVS SETUP //
  // try to initialise the default NVS partition
  esp_err_t errcode = nvs_flash_init();

  // if necessary, clear the flash and re-initialise
  if (errcode == ESP_ERR_NVS_NO_FREE_PAGES || errcode == ESP_ERR_NVS_NEW_VERSION_FOUND) 
  {
    report_esp_error(nvs_flash_erase());
    errcode = nvs_flash_init();
  }

  // if there is still something wrong, report and abort
  if (report_esp_error(errcode)) return false;

  // WIFI SETUP //
  // setup the default event loop, for handling WiFi events
  if (report_esp_error(esp_event_loop_create_default())) return false;

  // initialise the TCP/IP stack
  if (report_esp_error(esp_netif_init())) return false;

  // initialise the WiFi configuration to default config values
  wifi_init_config_t config = WIFI_INIT_CONFIG_DEFAULT();

  // initialise WiFi resources, and start the WiFi task
  if (report_esp_error(esp_wifi_init(&config))) return false;

  // set the WiFi to run in station mode
  if (report_esp_error(esp_wifi_set_mode(WIFI_MODE_STA))) return false;

  // set the WiFi configuration storage as RAM
  if (report_esp_error(esp_wifi_set_storage(WIFI_STORAGE_RAM))) return false;

  // set the bandwidth to HT40
  if (report_esp_error(esp_wifi_set_bandwidth(WIFI_IF_STA, WIFI_BW_HT40))) return false;

  // start WiFi, following current settings
  if (report_esp_error(esp_wifi_start())) return false;

  // set the ESP-NOW rate
  if (report_esp_error(esp_wifi_config_espnow_rate(WIFI_IF_STA, WIFI_PHY_RATE_MCS0_SGI))) return false;

  // set power saving type to none
  if (report_esp_error(esp_wifi_set_ps(WIFI_PS_NONE))) return false;

  // set the primary and secondary channels
  if (report_esp_error(esp_wifi_set_channel(CONFIG_LESS_INTERFERENCE_CHANNEL, WIFI_SECOND_CHAN_BELOW))) return false;

  // set the MAC address
  if (report_esp_error(esp_wifi_set_mac(WIFI_IF_STA, MAC_ADDR_RECV))) return false;

  // initialise ESP-NOW
  if (report_esp_error(esp_now_init())) return false;

  // set the ESP-NOW primary master key
  if (report_esp_error(esp_now_set_pmk((uint8_t *)"pmk1234567890123"))) return false;

  // CSI SETUP //
  // turn on promiscuous mode
  ESP_ERROR_CHECK(esp_wifi_set_promiscuous(true));

  // configure CSI settings
  wifi_csi_config_t csi_config = 
  {
    .lltf_en           = true,
    .htltf_en          = true,
    .stbc_htltf2_en    = true,
    .ltf_merge_en      = true,
    .channel_filter_en = true,
    .manu_scale        = false,
    .shift             = false
  };

  // set the CSI settings
  ESP_ERROR_CHECK(esp_wifi_set_csi_config(&csi_config));

  // register the CSI callback function
  ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(wifi_csi_rx_cb, NULL));

  // enable CSI
  ESP_ERROR_CHECK(esp_wifi_set_csi(true));

  return true;
}

static void wifi_csi_rx_cb(void *ctx, wifi_csi_info_t *info)
{
  // wifi callback function, triggers when packet received
  digitalWrite(WIFI_PIN, HIGH);

  // check if the packet info was correctly received
  if (!info || !info->buf) 
  {
    Serial.print("CSI info error in callback: ");
    Serial.println(esp_err_to_name(ESP_ERR_INVALID_ARG));
    return;
  }

  // check if this packet was sent by the correct sender
  if (!(memcmp(info->mac, MAC_ADDR_SEND_1, 6) || memcmp(info->mac, MAC_ADDR_SEND_2, 6) || memcmp(info->mac, MAC_ADDR_SEND_3, 6))) 
  {
    Serial.println("packet discarded, undesired sender");
    return;
  }

  // initialise variables for writing the packet to memory and set up time
  char line[CSI_SIZE];
  unsigned long time;
  char element[5];
  DateTime now = rtc.now();

  // update milliseconds if necessary
  new_second = now.second();
  if (new_second != old_second)
  {
    old_time = millis();
  }
  old_second = new_second;
  new_time = millis();
  time = new_time - old_time;

  // process packet header info into line
  wifi_csi_info_t d = info[0];
  sprintf(line, "CSI_DATA,STA," MACSTR ",%i,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%i,%u,%u,%u,%u,%u,%u,%u,%d,%u,%u,[", MAC2STR(info->mac), d.rx_ctrl.rssi, d.rx_ctrl.rate, d.rx_ctrl.sig_mode, d.rx_ctrl.mcs, 
          d.rx_ctrl.cwb, d.rx_ctrl.smoothing, d.rx_ctrl.not_sounding, d.rx_ctrl.aggregation, d.rx_ctrl.stbc, d.rx_ctrl.fec_coding, d.rx_ctrl.sgi, d.rx_ctrl.noise_floor, d.rx_ctrl.ampdu_cnt, d.rx_ctrl.channel, 
          d.rx_ctrl.secondary_channel, d.rx_ctrl.timestamp, d.rx_ctrl.ant, d.rx_ctrl.sig_len, d.rx_ctrl.rx_state, rtc_good, now.unixtime(), info->len);

  // write packet body into line
  for (int i = 0; i < info->len; i++) 
  {
    sprintf(element, "%d ", info->buf[i]);
    strcat(line, element);
  }

  // close the body array
  strcat(line, "]");

  // write to the correct csi array
  if (csi_switch)
  {
    strcpy(csi_data0[csi_idx], line);
    if (csi_idx < 39)
    {
      csi_idx++;
    }
    // when the end of the array is reached, clear the other array and write in it instead
    else
    {
      csi_idx = 0;
      csi_switch = !csi_switch;
      write_flag = true;
      memset(csi_data1, '\0', sizeof(csi_data1));
      //old_time = millis();
      Serial.println("switching to csi0, write_flag high");
    }
  }
  else
  {
    strcpy(csi_data1[csi_idx], line);
    if (csi_idx < 39)
    {
      csi_idx++;
    }
    // when the end of the array is reached, clear the other array and write in it instead
    else
    {
      csi_idx = 0;
      csi_switch = !csi_switch;
      write_flag = true;
      memset(csi_data0, '\0', sizeof(csi_data0));
      //old_time = millis();
      Serial.println("switching to csi1, write_flag high");
    }
  }
  digitalWrite(WIFI_PIN, LOW);
}
