# master-thesis-code
The codebase I created for my master thesis work. Contains software for ESP32 data collection and Python data processing.

## Jupyter
The Jupyter folder contains two Jupyter notebooks used to train a YOLO model and apply said model to a set of images created by sampling the video stream collected. They were originally run on the university's Jupyter server, hence them taking on this form.

## ESP32
The ESP32 folder contains the C++ code for the sender node and the receiver node. MAC addresses within the code should be changed accordingly when flashing a microcontroller. These are set up for PlatformIO. They require the following libraries:
- Adafruit BusIO
- Adafruit GFX
- Adafruit MPU6050
- Adafruit SSD1306
- Adafruit Unified Sensor
- RTClib
