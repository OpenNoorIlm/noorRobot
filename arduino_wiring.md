# Arduino Wiring Guide

This guide matches `hardware/esp32-os/arduino/arduino.ino`.
The Arduino is the companion motor and fan controller. It receives commands
from the ESP32 over SoftwareSerial and drives an L298N motor driver.

## Important architecture

The Arduino firmware currently controls:

- Four motor-control outputs for an L298N
- One fan output
- A serial link to the ESP32
- Eye and display commands as protocol-compatible no-op stubs

The temperature, distance, flame, line, hall, light, sound, and laser sensor
logic is implemented on the ESP32 firmware, not on this Arduino sketch.

## Pin map

| Arduino pin | Connect to | Function |
|---:|---|---|
| D10 | ESP32 GPIO17 / TX2 | SoftwareSerial RX; receives ESP32 commands |
| D11 | ESP32 GPIO16 / RX2 | SoftwareSerial TX; sends replies to ESP32 |
| D12 | Fan driver input | Fan on/off output |
| D5 | L298N Channel A IN2 | Right-side forward PWM |
| D3 | L298N Channel A IN1 | Right-side backward PWM |
| D6 | L298N Channel B IN3 | Left-side forward PWM |
| D9 | L298N Channel B IN4 | Left-side backward PWM |

The sketch uses:

```text
SoftwareSerial RX = D10
SoftwareSerial TX = D11
fanp = D12
rightFwd = D5
rightBwd = D3
leftFwd  = D6
leftBwd  = D9
```

## ESP32 serial connection

```text
ESP32 GPIO17 (TX2) --------> Arduino D10 (SoftwareSerial RX)
ESP32 GPIO16 (RX2) <-------- Arduino D11 (SoftwareSerial TX)
ESP32 GND ------------------> Arduino GND
```

The serial speed is 9600 baud, 8 data bits, no parity, and 1 stop bit.
Do not connect the ESP32 UART to a 5 V Arduino signal without level shifting.
If the Arduino TX signal is 5 V, place a voltage divider or level shifter on
the Arduino D11 -> ESP32 GPIO16 line.

## L298N motor-driver wiring

The firmware treats L298N Channel A as the right side and Channel B as the left
side. Two motors on each side are shown in parallel below.

```text
Arduino D3 (rightBwd)  -> L298N IN1
Arduino D5 (rightFwd)  -> L298N IN2
Arduino D6 (leftFwd)   -> L298N IN3
Arduino D9 (leftBwd)   -> L298N IN4

L298N OUT1/OUT2 -> right-side motor 1 and right-side motor 2
L298N OUT3/OUT4 -> left-side motor 1 and left-side motor 2
```

For parallel motors, confirm that the L298N channel current rating is adequate.
Each motor pair must be wired so both motors on the same side rotate in the
same physical direction. The right side is mirror-mounted, which is why the
firmware intentionally swaps its logical IN1/IN2 direction assignments.

Typical L298N power connections:

```text
Motor battery + -> L298N +12V/VMS (use the motor voltage required by motors)
Motor battery - -> L298N GND
Arduino GND -----> L298N GND
L298N 5V logic --> use only according to the L298N board/regulator design
```

Remove the L298N 5 V regulator jumper when the board's motor-supply voltage or
power arrangement requires it. Check the specific L298N module documentation.
Never feed motor voltage into an Arduino I/O pin.

## Fan wiring

Arduino D12 must drive the fan through a transistor, MOSFET, or relay module.
Do not connect the fan directly to D12.

Low-side MOSFET example:

```text
External fan supply + -----> Fan +
Fan - ----------------------> MOSFET drain
MOSFET source -------------> Supply GND
Arduino D12 --resistor-----> MOSFET gate
Arduino GND ---------------> Supply GND
```

Add a flyback diode across a brushed DC fan or relay coil when the driver does
not already include one. Size the supply and switching device for the fan's
startup current.

## Arduino power and grounding

- Power the Arduino from a regulated supply appropriate for the board.
- Power motors and the fan from their own appropriately rated supply.
- Tie Arduino GND, L298N GND, external driver GND, and ESP32 GND together.
- Keep motor current paths away from serial signal wires where practical.
- Add bulk capacitance near the motor-driver supply to reduce brownouts.

## Command and response test

The ESP32 sends text commands such as:

```text
forward(5,180)
backward(3,150)
right(90)
left(90)
stop(1)
fan on
fan off
fan status
```

The Arduino replies with `ok` for completed movement, fan, and protocol
commands. Test in this order:

1. Flash the sketch and verify the Arduino starts.
2. Test the ESP32-to-Arduino serial link with `stop(1)`.
3. Test the fan driver with the wheels lifted or disconnected.
4. Test one motor channel at low speed.
5. Test both channels with the robot safely raised.
6. Test forward, backward, left, right, and emergency stop.

Disconnect motor power while checking logic wiring. Keep wheels off the ground
until direction and stop behavior are confirmed.
