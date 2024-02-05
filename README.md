# Arduino Demo Prototype

## Setup

### Firmata Installation

Open the Arduino IDE and go to Tools -> Manage Libraries.  
Search for FirmataExpress by Alan Yorinks.  
Click Install.

### Running Firmata

Open the Arduino IDE and go to File -> Examples -> FirmataExpress -> FirmataExpress.  
Compile and upload the sketch to the Arduino Uno.  
Keep this sketch running to interface with the Arduino

### Running Python code

Open a terminal instance, clone the repository and cd to its directory.  
Create a virtual environment with `python -m venv venv`  
Activate the virtual environement with `./venv/Scripts/Activate.bat` for powershell or `source venv/bin/activate` for Mac or Linux  
Run the system with `python system.py`

## Pinout

0 = RK (don't use)  
1 = TK (don't use)  
2 = Trig - ultrasonic sensor  
3 = Echo - ultrasonic sensor  
4 = red LED - indicates speeding over max threshold  
5 = yellow LED - indicates speeding  
6 = blue LED - indicates ignition state  
7 = button - simulates turning on ignition  
8 = D4 - LCD  
9 = D5 - LCD  
10 = D6 - LCD  
11 = D7 - LCD  
12 = E - LCD  
13 = RS - LCD  

## LCD

VSS, RS, and K to ground  
A to 3.3V

LCD sometimes sends gibberish because the python library's initialization is unpredictable.  
If this occurs, open the lcd_test.ino sketch in the Arduino IDE and upload it to the Arduino UNO.  
If the Arduino is behaving normally, this should've fixed the issue and you can run the Firmata sketch again.  

## Schematic

Since there aren't enough male-to-male wires, male-to-female wires were used to connect the LCD.

![Alt text](images/schematic.png)

![Alt text](images/picture.png)