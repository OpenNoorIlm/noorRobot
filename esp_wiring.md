# ESP32 Wiring Guide

This guide matches `hardware/esp32-os/esp32/sensor_manager.h` and `robot_api.h`.
The ESP32 is the main robot computer: it provides Wi-Fi, the HTTP API on port
8083, the TFT UI, sensor readings, and the serial link to the Arduino motor
controller.

## Power rules

- Use a regulated 5 V supply for the ESP32 development board through its 5 V/VIN
  input or USB. Follow the board manufacturer's input limits.
- ESP32 GPIO is 3.3 V logic. Do not connect a 5 V signal directly to an ESP32
  GPIO. Use a level shifter or voltage divider where required.
- All modules and controllers must share GND with the ESP32.
- Motors, fans, servos, lasers, and other high-current loads need their own
  suitable supply. Do not power them from an ESP32 GPIO.
- Add a common ground between the external motor supply and the controller
  logic ground, unless an isolated interface is intentionally used.

## Sensor and actuator pin map

| Module | Module pin | ESP32 pin | Direction / notes |
|---|---|---:|---|
| DHT11 temperature/humidity | DATA | GPIO32 | Add the usual pull-up resistor if the sensor board does not include one. |
| IR obstacle sensor | DO | GPIO33 | Input; firmware treats LOW as obstacle. |
| Line tracking sensor | DO | GPIO34 | Input-only pin; firmware treats HIGH as on line. |
| Flame sensor | DO | GPIO35 | Input-only pin; firmware treats LOW as flame detected. |
| Photoresistor module | AO | GPIO36 | ADC input; GPIO36 is input-only. |
| Sound sensor module | AO | GPIO39 | ADC input; GPIO39 is input-only. |
| Hall/magnetic sensor | DO | GPIO21 | Input; firmware treats LOW as magnetic field detected. |
| Laser emitter or driver | IN | GPIO26 | Output; LOW at boot means off. Use a transistor/MOSFET driver. |
| Ultrasonic sensor | TRIG | GPIO13 | Output pulse. |
| Ultrasonic sensor | ECHO | GPIO14 | Input; level-shift a 5 V HC-SR04 echo to 3.3 V. |
| Pan/sweep servo | Signal | GPIO12 | Power servo separately; connect servo ground to common GND. |

For each 3-pin sensor module:

```text
VCC -> module-rated supply
GND -> ESP32 GND
SIG/DO/AO -> the GPIO listed above
```

Check the module's voltage rating before connecting VCC. A 5 V module output
must not be connected directly to an ESP32 input.

## Arduino serial link

The ESP32 talks to the companion Arduino through UART2 at 9600 baud:

| ESP32 | Arduino | Purpose |
|---|---|---|
| GPIO17 / TX2 | Arduino D10 / SoftwareSerial RX | ESP32 commands to Arduino |
| GPIO16 / RX2 | Arduino D11 / SoftwareSerial TX | Arduino replies to ESP32 |
| GND | GND | Common signal reference |

Wiring:

```text
ESP32 GPIO17 (TX2) --------> Arduino D10 (RX)
ESP32 GPIO16 (RX2) <-------- Arduino D11 (TX)
ESP32 GND ------------------> Arduino GND
```

Both sides use 3.3 V-compatible serial logic in the firmware design. Confirm
that the Arduino board's TX output is not 5 V before connecting it to GPIO16;
use a level shifter if necessary.

## TFT display wiring

The firmware is configured for a 2.8-inch ILI9341 SPI TFT. Connect the TFT as
follows:

| TFT pin | ESP32 pin | Purpose |
|---|---:|---|
| VCC | Board/module-rated supply | Check whether the breakout accepts 3.3 V or 5 V. |
| GND | GND | Common ground. |
| SCK/CLK | GPIO18 | VSPI clock. |
| MOSI/SDI | GPIO23 | Display data from ESP32. |
| MISO/SDO | GPIO19 | Display data to ESP32. |
| CS | GPIO5 | Display chip select. |
| DC/RS | GPIO2 | Data/command select. |
| RST/RESET | GPIO4 | Display reset. |
| LED/BL | GPIO27 | Backlight control; firmware sets it HIGH at boot. |

The `TFT_eSPI` library must use these same pins in its `User_Setup`:

```text
TFT_CS=5, TFT_DC=2, TFT_RST=4
TFT_MOSI=23, TFT_MISO=19, TFT_CLK=18
```

Do not connect the display backlight directly if the display requires more
current than a GPIO can provide; use a transistor or the breakout's designed
backlight input.

## XPT2046 touch wiring

The touch controller shares the SPI signal bus but has its own chip select.
The firmware uses manual HSPI with polling, so no touch IRQ wire is required:

| XPT2046 pin | ESP32 pin | Purpose |
|---|---:|---|
| VCC | 3.3 V/module-rated supply | Follow the breakout rating. |
| GND | GND | Common ground. |
| T_CLK/SCK | GPIO14 | Touch SPI clock. |
| T_DIN/MOSI | GPIO13 | Data from ESP32 to touch controller. |
| T_DO/MISO | GPIO12 | Data from touch controller. |
| T_CS | GPIO22 | Touch chip select. |
| T_IRQ | Not connected | `TOUCH_IRQ=-1`; firmware polls the controller. |

Important: GPIO12, GPIO13, and GPIO14 are also used by the ultrasonic sensor
and pan servo in `sensor_manager.h` (TRIG=13, ECHO=14, SERVO=12). The current
firmware therefore has a hardware pin conflict between touch SPI and those
devices. Reassign one group in the firmware before wiring all of them together.

## SD card wiring

The SD card uses the same VSPI signal wires as the TFT and has a separate CS:

| SD pin | ESP32 pin | Purpose |
|---|---:|---|
| VCC | Module-rated supply | Use a 3.3 V-compatible SD breakout. |
| GND | GND | Common ground. |
| SCK/CLK | GPIO18 | Shared VSPI clock. |
| MOSI/DI | GPIO23 | Shared VSPI data to card. |
| MISO/DO | GPIO19 | Shared VSPI data from card. |
| CS | GPIO21 | SD card chip select. |

The TFT and SD card may share SCK, MOSI, and MISO, but each device must have
its own CS and only the selected device should drive MISO. The firmware calls
`SD.begin(21)`.

Important: GPIO21 is also `SM_HALL_PIN` in `sensor_manager.h`. This is another
firmware pin conflict. Move the SD CS or Hall sensor to a free GPIO and update
the corresponding source definition before using both.

## Audio wiring

The audio header defines two built-in ESP32 DAC outputs and an optional PWM
buzzer:

| Audio connection | ESP32 pin | Purpose |
|---|---:|---|
| DAC right input | GPIO25 / DAC channel 1 | Analog audio to amplifier. |
| DAC left input | GPIO26 / DAC channel 2 | Analog audio to amplifier. |
| Buzzer driver input | GPIO27 | Optional PWM beep output. |
| Amplifier GND | GND | Common ground. |

Connect GPIO25 and GPIO26 to the left/right inputs of a PAM8403 or another
line-level amplifier through the module's recommended coupling/filtering. Then
connect the amplifier to the speakers. Do not connect a speaker directly to an
ESP32 GPIO or DAC pin. Power the amplifier from its specified supply and share
the logic ground.

For a buzzer, connect GPIO27 to a buzzer driver or an active buzzer module as
specified by that module. Do not drive a high-current buzzer directly from the
GPIO.

There are two current firmware conflicts to resolve:

- GPIO26 is both `AUDIO_DAC_LEFT` and `SM_LASER_PIN`.
- GPIO27 is both `AUDIO_BUZZER_PIN` and `TFT_BL`.

Either reassign the conflicting pins in the firmware or choose which function
is active. The DAC output and buzzer should not be wired as independent active
peripherals until these conflicts are fixed.

## Network/API connections

After wiring and flashing:

- ESP32 joins Wi-Fi using `wifi_manager.h`.
- The robot HTTP API listens on port `8083`.
- Set NoorRobot's `ESP32_URL` to the ESP32 address, for example:

```env
ESP32_URL=http://192.168.1.50:8083
```

Useful checks:

```text
GET /help
GET /temperature
GET /temperature_esp32
GET /distance?q=90
GET /forward?q=1&speed=180
GET /stop
```

## Bring-up order

1. Connect GND between the ESP32 and every logic module.
2. Test the ESP32 with sensors disconnected from high-current loads.
3. Verify DHT, ultrasonic, and digital sensor readings.
4. Test the servo with a separate 5-6 V supply and common GND.
5. Test the UART link with the Arduino motor driver disabled.
6. Connect motor/fan/laser drivers last and test `stop` first.

Never connect a motor, fan, laser diode, or servo power lead directly to an
ESP32 GPIO.
