// Sender_logger_RTOS


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

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <RTClib.h>
#include <Wire.h>

RTC_DS1307 rtc;

Adafruit_MPU6050 imu;

// WiFi parameters
#define CONFIG_LESS_INTERFERENCE_CHANNEL    11
#define CONFIG_SEND_FREQUENCY               100           // in hz

// string length parameters
#define IMU_SIZE                            61
#define TIME_SIZE                           24
#define FILENAME_SIZE                       26

// startup leds
#define WIFI_PIN    D0
#define SD_PIN      D2

// mac addresses
static const uint8_t MAC_ADDR_SEND[] = {0x1a, 0x00, 0x03, 0x00, 0x00, 0x00};
static const uint8_t MAC_ADDR_RECV[] = {0x1a, 0x03, 0x00, 0x00, 0x00, 0x00};
static const uint8_t MAC_ADDR_BROAD[] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff};

uint8_t pkt_count = 0;

// define tasks
void task_write_csv(void *pvParameters);
void task_save_imu(void *pvParameters);
void task_send_csi(void *pvParameters);
void task_save_img(void *pvParameters);

static portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;

// global variables
int imu_idx = 0;
bool imu_switch = false;
int imu_idx_last = 0;
char imu_name[20];

char imu_data0[200][IMU_SIZE+TIME_SIZE];
char imu_data1[200][IMU_SIZE+TIME_SIZE];

unsigned long new_time = 0;
unsigned long old_time = 0;
uint8_t new_second = 0;
uint8_t old_second = 0;

bool wifi_good;
bool rtc_good;
bool sd_good;
bool imu_good;

//functions
bool report_esp_error(esp_err_t);
void generate_timestamp(char*, DateTime*, bool, unsigned long);
bool wifi_setup();
bool sd_setup();
bool rtc_setup();
bool imu_setup();


void setup() 
{
  Serial.begin(115200);

  // set up led pins
  pinMode(WIFI_PIN, OUTPUT);
  pinMode(SD_PIN, OUTPUT);

  // run setup functions, turning on leds when appropriate to indicate success
  imu_good = imu_setup();
  sd_good = sd_setup();
  if(sd_good) digitalWrite(SD_PIN, HIGH);
  rtc_good = rtc_setup();
  wifi_good = wifi_setup();
  if(wifi_good) digitalWrite(WIFI_PIN, HIGH);

  // initialise tasks
  xTaskCreatePinnedToCore(
    task_send_csi, "Task Send CSI"
    ,
    3072  // stack size
    ,
    NULL  
    ,
    3  // priority
    ,
    NULL  
    ,
    1 // core
  );
  xTaskCreatePinnedToCore(
    task_save_imu, "Task Save IMU" 
    ,
    4096  // stack size
    ,
    NULL  
    ,
    3  // priority
    ,
    NULL 
    ,
    1 // core
  );
  xTaskCreatePinnedToCore(
    task_write_csv, "Task Write csv"  
    ,
    4096  // stack size
    ,
    NULL  
    ,
    2  // priority
    ,
    NULL                       
    ,
    0 // core
  );
}

void loop() 
{
  // nothing happens here

}

void task_send_csi(void *pvParameters)
{
  // send a csi packet, runs every 1/fs

  // get peer information from setup
  esp_now_peer_info_t recv;
  bool send_failure;
  esp_now_get_peer(MAC_ADDR_RECV, &recv);

  // set delay time
  const TickType_t xDelay = (1000 / CONFIG_SEND_FREQUENCY) / portTICK_PERIOD_MS;

  for(;;)
  {
    // send a packet
    send_failure = report_esp_error(esp_now_send(recv.peer_addr, &pkt_count, sizeof(uint8_t)));
    if(!send_failure)
    {
      digitalWrite(WIFI_PIN, HIGH);
    }
    else
    {
      digitalWrite(WIFI_PIN, LOW);
    }

    // wait the specified time before sending again
    vTaskDelay( xDelay ); 
  }
  vTaskDelete( NULL );
}

void task_save_imu(void *pvParameters)
{
  // saves imu data to memory once every 1/fs

  // initialise delay, time variables, data and csv line variables
  const TickType_t xDelay = (1000 / CONFIG_SEND_FREQUENCY) / portTICK_PERIOD_MS;
  char line[IMU_SIZE + TIME_SIZE]{};
  char timestamp[TIME_SIZE]{};
  unsigned long time;
  sensors_event_t a, g, temp;
  DateTime now;

  for(;;)
  {
    // get imu data
    imu.getEvent(&a, &g, &temp);
    
    // get time
    now = rtc.now();
    new_second = now.second();
    if (new_second != old_second)
    {
      old_time = millis();
    }
    old_second = new_second;
    new_time = millis();
    time = new_time - old_time;

    // delete everything in the strings, so they can be used again, then fill them with new data
    memset(timestamp, '\0', TIME_SIZE);
    memset(line, '\0', IMU_SIZE + TIME_SIZE);
    generate_timestamp(timestamp, &now, false, time);
    sprintf(line, "%s,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f", timestamp, a.acceleration.x, a.acceleration.y, a.acceleration.z, g.gyro.x, g.gyro.y, g.gyro.z);

    // write to the appropriate array, locking while we write to ensure stability
    if(imu_switch == false)
    {
      taskENTER_CRITICAL(&lock);
      strcpy(imu_data0[imu_idx], line);
      imu_idx++;
      taskEXIT_CRITICAL(&lock);
    }
    else
    {
      taskENTER_CRITICAL(&lock);
      strcpy(imu_data1[imu_idx], line);
      imu_idx++;
      taskEXIT_CRITICAL(&lock);
    }

    vTaskDelay( xDelay ); 
  }
  vTaskDelete( NULL );
}

void task_write_csv(void *pvParameters)
{
  // writes the internal imu array to the csv on the sd card, once every 2 seconds

  // initialise variables
  const TickType_t xDelay = 2000 / portTICK_PERIOD_MS;
  char timestamp[TIME_SIZE]{};
  unsigned long time;
  DateTime now;
  File imu_file;
  
  for(;;)
  {
    // update which imu array we are saving new data in
    Serial.println("started write all");
    taskENTER_CRITICAL(&lock);
    imu_idx_last = imu_idx;
    imu_idx = 0;
    imu_switch = !imu_switch;
    taskEXIT_CRITICAL(&lock);

    // if the sd is functional, do a write
    if(sd_good)
    {
      // open imu csv
      imu_file = SD.open(imu_name, FILE_APPEND);
      if(!imu_file)
      {
        Serial.println("Failed to open imu file for writing");
      }
      else
      {
        Serial.println("File loaded");
      }
  
      // write to imu csv
      Serial.println("Writing csv");
      if(imu_switch == false)
      {
        for(int i=0;i<imu_idx_last;i++)
        {
          imu_file.println(imu_data1[i]);
        }
      }
      else
      {
        for(int i=0;i<imu_idx_last;i++)
        {
          imu_file.println(imu_data0[i]);
        }
      }
      
      // close imu csv
      imu_file.close();
      Serial.println("imu csv saved");
    }
    else
    {
      Serial.println("Unknown SD card failure");
    }

    vTaskDelay( xDelay ); 
  }
  vTaskDelete( NULL );
}

bool report_esp_error(esp_err_t err)
{
  // report an esp error in a readable way
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

bool imu_setup()
{
  // setup IMU and report on failure if it occurs
  if (!imu.begin(0x69)) 
  {
    Serial.println("Failed to find IMU");
    return false;
  }
  Serial.println("IMU Found!");

  imu.setAccelerometerRange(MPU6050_RANGE_2_G);
  Serial.println("Accelerometer range set to: +- 2G");
  imu.setGyroRange(MPU6050_RANGE_250_DEG);
  Serial.println("Gyro range set to: +- 250 deg/s");
  imu.setFilterBandwidth(MPU6050_BAND_44_HZ);
  Serial.println("Filter bandwidth set to: 44 Hz");

  return true;
}

bool rtc_setup()
{
  // setup rtc and report on failure if it occurs
  if (!rtc.begin()) 
  {
    Serial.println("Failed to find RTC");
    return false;
  }
  Serial.println("RTC Found!");

  // if starting a new measurement set, set date and time to compile time
  if(!SD.exists("/imu_data0.csv"))
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
  // setup SD card and report on failure if it occurs

  // initialise
  if(!SD.begin(21))
  {
    Serial.println("Card Mount Failed");
    return false;
  }
  uint8_t cardType = SD.cardType();

  // get card type
  if(cardType == CARD_NONE)
  {
    Serial.println("No SD card attached");
    return false;
  }

  Serial.print("SD Card Type: ");
  if(cardType == CARD_MMC)
  {
    Serial.println("MMC");
  } else if(cardType == CARD_SD){
    Serial.println("SDSC");
  } else if(cardType == CARD_SDHC){
    Serial.println("SDHC");
  } else {
    Serial.println("UNKNOWN");
  }

  // make a new csv and generate its header
  int imu_num = 0;
  sprintf(imu_name, "/imu_data%i.csv", imu_num);
  while(SD.exists(imu_name))
  {
    imu_num++;
    memset(imu_name, '\0', 20);
    sprintf(imu_name, "/imu_data%i.csv", imu_num);
  } 

  File imu_file = SD.open(imu_name, FILE_WRITE);
  imu_file.println("timestamp,accX,accY,accZ,gyroX,gyroY,gyroZ");
  imu_file.close();

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
  if (report_esp_error(esp_wifi_set_mac(WIFI_IF_STA, MAC_ADDR_SEND))) return false;

  // initialise ESP-NOW
  if (report_esp_error(esp_now_init())) return false;

  // set the ESP-NOW primary master key
  if (report_esp_error(esp_now_set_pmk((uint8_t *)"pmk1234567890123"))) return false;

  // define the receiver as an ESP-NOW peer
  esp_now_peer_info_t recv = 
  {
    .channel   = CONFIG_LESS_INTERFERENCE_CHANNEL,
    .ifidx     = WIFI_IF_STA,    
    .encrypt   = false   
  };

  memcpy(recv.peer_addr, MAC_ADDR_RECV, sizeof(uint8_t[6]));

  // add the peer to the ESP-NOW network
  if (report_esp_error(esp_now_add_peer(&recv))) return false;

  // finally, report on the sending parameters
  Serial.printf("Channel: %d\nFrequency: %d Hz\nMAC address: " MACSTR "\n", CONFIG_LESS_INTERFERENCE_CHANNEL, CONFIG_SEND_FREQUENCY, (MAC_ADDR_SEND));

  return true;
}

void generate_timestamp(char* timestamp, DateTime* now, bool img, unsigned long milli = 0)
{
  // generate a timestamp in a specific desired format
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
