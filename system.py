import asyncio
from datetime import datetime


from pymata4 import pymata4
import numpy as np
import matplotlib.pyplot as plt


from libs.LiquidCrystal import LiquidCrystal
import dig_calls


# Timing constants
CYCLE_TIME = 0.1
POLL_COUNT_DISTANCE = 100
POLL_COUNT_POTENTIOMETER = 25

# Arduino pins
BUTTON_PIN = 12
TRIG_PIN = 11
ECHO_PIN = 10
POTENTIOMETER_PIN = 0
IGNITION_LED_PIN = 7
SPEEDING_PIN = 6
SPEEDING_ABOVE_MAX_PIN = 5

# DIG constants and message codes
SEND_DIG = False
SERIAL_NO = 'CXF7216F55ED'
IGNITION_CODE = 10000
ENGINE_SPEED_CODE = 107
ODOMETER_CODE = 5
SPEEDING_CODE = 35307
SPEEDING_ABOVE_MAX_CODE = 35308

# Callback data indices
CB_PIN_MODE = 0
CB_PIN = 1
CB_VALUE = 2
CB_TIME = 3


def button_press_handler(data):
    '''
    Pymata callback for button
    '''
    loop.create_task(button_press_coroutine(data))


async def button_press_coroutine(data):
    '''
    Actual callback for button
    '''
    # Log each button press with time stamp
    date_time = datetime.fromtimestamp(data[CB_TIME])
    print(f'Pin: {data[CB_PIN]} Value: {data[CB_VALUE]} Time Stamp: {date_time.strftime("%Y-%m-%d %H:%M:%S")}')

    # On button press, check to make sure button is held for a time before sending DIG call
    if data[CB_VALUE] == 1:
        ignition = True
        end_time = asyncio.get_running_loop().time() + 1
        while asyncio.get_running_loop().time() < end_time:
            pin_value = await loop.run_in_executor(None, board.digital_read, data[CB_PIN])
            if pin_value[0] == 0:
                ignition = False
                break
        # Change the ignition state when the button is pressed
        if ignition and board.digital_read(data[CB_PIN])[0] == 1 and data[CB_TIME] - state['last_ignition'] > 1:
            if not state['ignition']:
                print('Ignition On')
                state['ignition'] = 1
            else:
                print('Ignition Off')
                state['ignition'] = 0

            state['last_ignition'] = data[CB_TIME]

            board.digital_write(IGNITION_LED_PIN, state['ignition'])
            
            # DIG call
            if SEND_DIG:
                try:
                    res = dig_calls.send_GenericStatusRecord(
                        token=token,
                        serialNo=SERIAL_NO,
                        code=IGNITION_CODE,
                        value=state['ignition'],
                        timestamp=date_time
                    )
                    assert res
                except AssertionError:
                    print('sending GeneritStatusRecord failed')


async def potentiometer_log_handler(data):
    '''
    Callback for logging potentiometer readings
    '''
    value, date = data
    date_time = datetime.fromtimestamp(date)

    # Convert by max_value to send / max_potentiometer value / DIG conversion factor
    converted_value = int(value * 5000 / 1023 / 0.25)
    print(f'Value: {value} | Converted Value: {converted_value*0.25} RPM | Timestamp: {date_time}')

    # Send DIG call
    if SEND_DIG:
        try:
            res = dig_calls.send_GenericStatusRecord(
                token=token,
                serialNo=SERIAL_NO,
                code=ENGINE_SPEED_CODE,
                value=converted_value,
                timestamp=date_time)
            assert res
        except AssertionError:
            print('sending GenericStatusRecord failed')


async def distance_log_handler(data):
    '''
    Callback for logging the distance measurements
    '''
    # Clean data for 0s and false spikes when sensor echo pin "misses" the trigger
    readings = np.array([reading for reading in data if reading[1] != 0 and reading[0] < 200])
    if len(readings) < 3:
        return False
    distances = readings[:,0]
    timestamps = readings[:, 1]
    velocities = np.diff(distances)

    # Plot Distance and velocity vs time actual arduino uses cm and s, we simulate as km and h
    ax1.plot(timestamps, distances, label='distance', color='b')
    ax2.plot(timestamps[1:], velocities, label='velocity', color = 'g')

    # Get the points of max error to log
    log_data = await curve_logging_helper(distances, timestamps, [])
    log_data.append([distances[-1], timestamps[-1]])

    for log in log_data:
        # Plot point of max error
        ax1.plot(log[1], log[0], marker='o', markersize=5, color='red')

        # Send the point through DIG
        if SEND_DIG:
            try:
                res = dig_calls.send_GenericStatusRecord(
                    token=token,
                    serialNo=SERIAL_NO,
                    code=ODOMETER_CODE,
                    value=int(log[0] * 10),
                    timestamp=datetime.fromtimestamp(log[1]))
                assert res
            except AssertionError:
                print('sending GenericStatusRecord failed')

    plt.savefig('logs/distance_logs.jpg')


async def curve_logging_helper(values, timestamps, max_diffs):
    '''
    Recursive helper function to find values with the maximum error
    '''
    # Prevent divide by 0 error or having too many points sending through DIG
    if len(values) == 1 or len(max_diffs) >= POLL_COUNT_DISTANCE * CYCLE_TIME / 2.5:
        return max_diffs
    
    # "Draw" line between first and last point
    slope = (values[-1] - values[0]) / (timestamps[-1] - timestamps[0])
    y_int = values[0] - timestamps[0] * slope
    preds = timestamps * slope + y_int

    # Find point that is furthest from line
    diffs = np.abs(values - preds)
    i = np.argmax(diffs)

    # If error is significant, add the point and keep logging
    if (diffs[i]) > 20:
        max_diffs.append([values[i], timestamps[i]])
        max_diffs = await curve_logging_helper(values[:i+1], timestamps[:i+1], max_diffs)
        max_diffs = await curve_logging_helper(values[i:], timestamps[i:], max_diffs)
    return max_diffs


def speeding_check(x1, x0):
    '''
    Checks the speed (from Ultrasonic sensor)
    '''
    v1, t1 = x1
    v0, t0 = x0

    # Clean data
    if v1 > 200 or v0 > 200:
        return False
    
    speed = abs(v1 - v0)
    
    # Determine if speeding 
    if speed > 10:
        # If speeding above maximum threshold
        if speed > 20:
            board.digital_write(SPEEDING_ABOVE_MAX_PIN, 1)
            board.digital_write(SPEEDING_PIN, 0)
            code = SPEEDING_ABOVE_MAX_CODE
        # Speeding above posted limit, but below threshold
        else:
            board.digital_write(SPEEDING_PIN, 1)
            board.digital_write(SPEEDING_ABOVE_MAX_PIN, 0)
            code = SPEEDING_CODE

        # Prevent sending multiple logs for the same speeding incident
        if t1 - state['last_speeding'] > 2:
            state['last_speeding'] = t1
            ax2.plot(t1, v1-v0, marker='o', markersize=5, color='m')
            print(f'Speeding at: {speed}')

            # Send DIG all
            if SEND_DIG:
                try:
                    res = dig_calls.send_GenericStatusRecord(
                        token=token,
                        serialNo=SERIAL_NO,
                        code=code, value=1,
                        timestamp=datetime.fromtimestamp(t1))
                    assert res
                except AssertionError:
                    print('sending GenericStatusRecord failed')
    # No speeding detected
    else:
        board.digital_write(SPEEDING_PIN, 0)
        board.digital_write(SPEEDING_ABOVE_MAX_PIN, 0)

async def main(board):
    '''
    Main function
    '''
    # Button simulates ignition button - hold down to turn ignition on/off
    board.set_pin_mode_digital_input(BUTTON_PIN, callback=button_press_handler)
    
    # Potentiometer sets the simulated engine speed
    board.set_pin_mode_analog_input(POTENTIOMETER_PIN)

    # Ultrasonic sensor simulates the odometer
    board.set_pin_mode_sonar(TRIG_PIN, ECHO_PIN)

    # Blue LED shows state of ignition
    board.set_pin_mode_digital_output(IGNITION_LED_PIN)

    # Yello LED on if speeding above posted limit
    board.set_pin_mode_digital_output(SPEEDING_PIN)

    # Red LED on if speeding above maximum threshold
    board.set_pin_mode_digital_output(SPEEDING_ABOVE_MAX_PIN)

    ticks = 0
    distance_readings = []
    while True:        
        # Read values from inputs
        potentiometer_reading = board.analog_read(POTENTIOMETER_PIN)
        distance_reading = board.sonar_read(TRIG_PIN)
        distance_readings.append(distance_reading)

        # Constantly show the potentiomter output on the LCD
        lcd.clear()
        lcd.set_cursor(2, 0)
        lcd.print('Pot Reading:')
        lcd.set_cursor(6,1)
        lcd.print(str(potentiometer_reading[0]))

        # Check for speeding
        if len(distance_readings) > 2:
            speeding_check(distance_readings[-1], distance_readings[-2])

        # Log potentiometer value at set intervals
        if ticks % POLL_COUNT_POTENTIOMETER == 0 and ticks != 0:
            loop.create_task(potentiometer_log_handler(potentiometer_reading))

        # Log the distance sensor values at set intervals
        if ticks % POLL_COUNT_DISTANCE == 0 and ticks != 0:
            print('Logging Distance', datetime.now())
            loop.create_task(distance_log_handler(distance_readings[-POLL_COUNT_DISTANCE:]))

        ticks += 1
        await asyncio.sleep(CYCLE_TIME)


# Authentication calls for MyAdmin and DIG
if SEND_DIG:
    try:
        MyAdmin_authenticate_flag, userId, sessionId = dig_calls.authenticate_MyAdmin()
        assert MyAdmin_authenticate_flag

        DIG_authenticate_flag, token, tokenExpiration, refreshToken, refreshTokenExpiration = dig_calls.authenticate_DIG()
        assert DIG_authenticate_flag
    except AssertionError:
        print('Authentication Error')


# Initialization
loop = asyncio.get_event_loop()
board = pymata4.Pymata4()
lcd = LiquidCrystal(9, 8, 4, 3, 2, 13, board)
state = {
    'ignition': False,
    'last_ignition': 0,
    'distance': 0,
    'last_speeding': 0,
}
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
ax1.set_title('Distance vs Time')
ax1.set_xlabel('Time (h)')
ax1.set_ylabel('Distance (km)')
ax2.set_title('Velocity vs Time')
ax2.set_xlabel('Time (h)')
ax2.set_ylabel('Velocity (km/h)')
plt.tight_layout()

# Run the program
try:
    loop.run_until_complete(main(board))
except KeyboardInterrupt:
    lcd.clear()
    board.shutdown()
    print('Program Termintated')