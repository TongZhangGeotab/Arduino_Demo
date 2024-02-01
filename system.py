import asyncio
from datetime import datetime


from pymata4 import pymata4
import numpy as np
import matplotlib.pyplot as plt


from libs.LiquidCrystal import LiquidCrystal
import dig_calls


SEND_DIG = False

CYCLE_TIME = 0.1
POLL_COUNT = 50
SERIAL_NO = 'CXF7216F55ED'

# Arduino pins
BUTTON_PIN = 12
POTENTIOMETER_PIN = 0
LED_PIN = 7
TRIG_PIN = 11
ECHO_PIN = 10

# Message codes
IGNITION_CODE = 10000
ENGINE_SPEED_CODE = 107
ODOMETER_CODE = 5

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
    date_time = datetime.fromtimestamp(data[CB_TIME]).strftime('%Y-%m-%d %H:%M:%S')
    print(f'Pin: {data[CB_PIN]} Value: {data[CB_VALUE]} Time Stamp: {date_time}')

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
        if ignition and board.digital_read(data[CB_PIN])[0] == 1:
            if not state['ignition']:
                print('Ignition On')
                state['ignition'] = 1
            else:
                print('Ignition Off')
                state['ignition'] = 0

            board.digital_write(LED_PIN, state['ignition'])
            
            # DIG call
            if SEND_DIG:
                try:
                    res = dig_calls.send_GenericStatusRecord(token=token, serialNo=SERIAL_NO, code=IGNITION_CODE, value=state['ignition'], timestamp=datetime.now())
                    assert res
                except AssertionError:
                    print('sending GeneritStatusRecord failed')


async def potentiometer_log_handler(data):
    '''
    Callback for logging potentiometer readings
    '''
    value, date = data
    converted_value = value * 4000 / 800 / 0.25
    
    date_time = datetime.fromtimestamp(date).strftime('%Y-%m-%d %H:%M:%S')
    print(f'Pin: {POTENTIOMETER_PIN} Value: {value} Time Stamp: {date_time}')

    if SEND_DIG:
        try:
            res = dig_calls.send_GenericStatusRecord(token=token, serialNo=SERIAL_NO, code=ENGINE_SPEED_CODE, value=converted_value, timestamp=datetime.now())
            assert res
        except AssertionError:
            print('sending GenericStatusRecord failed')


async def distance_log_handler(data):
    '''
    Callback for logging the distance measurements
    '''
    readings = np.array([reading for reading in data if reading[1] != 0 and reading[0] < 200])
    distances = readings[:,0]
    timestamps = readings[:, 1]

    plt.plot(timestamps, distances, label='distance', color='b')

    # velocities = np.diff(distances)
    # accelerations = np.diff(velocities)
    # plt.plot(timestamps[1:], velocities, label='Velocity')
    # plt.plot(timestamps[1:-1], accelerations, label='Acceleration')
    # plt.legend()
    
    log_data = await curve_logging_helper(distances, timestamps, [])
    log_data.append([distances[-1], timestamps[-1]])

    for log in log_data:
        plt.plot(log[1], log[0], marker='o', markersize=5, color='red')

        if SEND_DIG:
            try:
                res = dig_calls.send_GenericStatusRecord(token=token, serialNo=SERIAL_NO, code=ODOMETER_CODE, value=int(log[0] / 100), timestamp=datetime.fromtimestamp(log[1]))
                assert res
            except AssertionError:
                print('sending GenericStatusRecord failed')

    plt.savefig('logs/distance_logs.jpg')


async def curve_logging_helper(values, timestamps, max_diffs):
    '''
    Recursive helper function to find values with the maximum error
    '''
    if len(values) == 1 or len(max_diffs) >= POLL_COUNT * CYCLE_TIME:
        return max_diffs
    slope = (values[-1] - values[0]) / (timestamps[-1] - timestamps[0])
    y_int = values[0] - timestamps[0] * slope
    preds = timestamps * slope + y_int
    diffs = np.abs(values - preds)
    i = np.argmax(diffs)
    if (diffs[i]) > 20:
        max_diffs.append([values[i], timestamps[i]])
        max_diffs = await curve_logging_helper(values[:i+1], timestamps[:i+1], max_diffs)
        max_diffs = await curve_logging_helper(values[i:], timestamps[i:], max_diffs)
    return max_diffs


async def main(board):
    '''
    Main function
    '''
    # board.set_pin_mode_digital_input(BUTTON_PIN, callback=button_press_handler)
    board.set_pin_mode_analog_input(POTENTIOMETER_PIN)
    board.set_pin_mode_digital_output(LED_PIN)
    board.set_pin_mode_sonar(TRIG_PIN, ECHO_PIN)

    ticks = 0
    distance_readings = []
    while True:        
        potentiometer_reading = board.analog_read(POTENTIOMETER_PIN)
        distance_reading = board.sonar_read(TRIG_PIN)
        distance_readings.append(distance_reading)

        if ticks % POLL_COUNT == 0 and ticks != 0:
            print('Logging')
            loop.create_task(potentiometer_log_handler(potentiometer_reading))
            loop.create_task(distance_log_handler(distance_readings))
            distance_readings = []

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
state = {
    'ignition': False,
    'distance': 0
}


# Run the program
try:
    start_time = datetime.now()
    loop.run_until_complete(main(board))
except KeyboardInterrupt:
    board.shutdown()
    print('Program Termintated')