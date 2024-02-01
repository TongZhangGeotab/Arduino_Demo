import time

LCD_CLEARDISPLAY =0x01
LCD_RETURNHOME =0x02
LCD_ENTRYMODESET =0x04
LCD_DISPLAYCONTROL =0x08
LCD_CURSORSHIFT =0x10
LCD_FUNCTIONSET =0x20
LCD_SETCGRAMADDR =0x40
LCD_SETDDRAMADDR =0x80

# flags for display entry mode
LCD_ENTRYRIGHT =0x00
LCD_ENTRYLEFT =0x02
LCD_ENTRYSHIFTINCREMENT =0x01
LCD_ENTRYSHIFTDECREMENT =0x00

# flags for display on/off control
LCD_DISPLAYON =0x04
LCD_DISPLAYOFF =0x00
LCD_CURSORON =0x02
LCD_CURSOROFF =0x00
LCD_BLINKON =0x01
LCD_BLINKOFF =0x00

# flags for display/cursor shift
LCD_DISPLAYMOVE =0x08
LCD_CURSORMOVE =0x00
LCD_MOVERIGHT =0x04
LCD_MOVELEFT =0x00

# flags for function set
LCD_8BITMODE =0x10
LCD_4BITMODE =0x00
LCD_2LINE =0x08
LCD_1LINE =0x00
LCD_5x10DOTS =0x04
LCD_5x8DOTS =0x00


class LiquidCrystal:
    def __init__(self, rs, e, d4, d5, d6, d7, board):
        self.board = board
        self.row_offsets = [0x00, 0x40, 0x00 + 16, 0x40 + 16]
        self.rs_pin = rs
        self.e_pin = e
        self.data_pins = [d4, d5, d6, d7]
        self.display_function = LCD_4BITMODE | LCD_2LINE | LCD_5x8DOTS
        self.numlines = 1

        self.board.set_pin_mode_digital_output(self.rs_pin)
        self.board.set_pin_mode_digital_output(self.e_pin)

        for pin in self.data_pins:
            self.board.set_pin_mode_digital_output(pin)
        time.sleep(0.05)

        self.board.digital_write(self.rs_pin, 0)
        self.board.digital_write(self.e_pin, 0)

        # Set to 4 bit mode
        self.write4bits(0x03)
        time.sleep(0.0045)
        self.write4bits(0x03)
        time.sleep(0.0045)
        self.write4bits(0x03)
        time.sleep(0.00015)
        self.write4bits(0x02)

        self.command(LCD_FUNCTIONSET | self.display_function)
        
        self.display_control = LCD_DISPLAYON | LCD_CURSOROFF | LCD_BLINKOFF
        self.display()
        self.clear()

        self.display_mode = LCD_ENTRYLEFT | LCD_ENTRYSHIFTDECREMENT
        self.command(LCD_ENTRYMODESET | self.display_mode)

    def clear(self):
        self.command(LCD_CLEARDISPLAY)
        time.sleep(0.002)

    def home(self):
        self.command(LCD_RETURNHOME)
        time.sleep(0.002)

    def set_cursor(self, col, row):
        self.command(LCD_SETDDRAMADDR | (col + self.row_offsets[row]))

    def no_display(self):
        self.display_control = self.display_function & (~LCD_DISPLAYON & 0xff)
        self.command(LCD_DISPLAYCONTROL | self.display_control)

    def display(self):
        self.display_control = self.display_control | LCD_DISPLAYON
        self.command(LCD_DISPLAYCONTROL | self.display_control)

    def no_cursor(self):
        self.display_control = self.display_control & (~LCD_CURSORON & 0xff)
        self.command(LCD_DISPLAYCONTROL | self.display_control)

    def cursor(self):
        self.display_control = self.display_control | LCD_CURSORON
        self.command(LCD_DISPLAYCONTROL | self.display_control)

    def no_blink(self):
        self.display_control = self.display_control & (~LCD_BLINKON & 0xff)
        self.command(LCD_DISPLAYCONTROL | self.display_control)

    def blink(self):
        self.display_control = self.display_control | LCD_BLINKON
        self.command(LCD_DISPLAYCONTROL | self.display_control)

    def scroll_display_left(self):
        self.command(LCD_CURSORSHIFT | LCD_DISPLAYMOVE | LCD_MOVELEFT)

    def scroll_display_right(self):
        self.command(LCD_CURSORSHIFT | LCD_DISPLAYMOVE | LCD_MOVERIGHT)

    def left_to_right(self):
        self.display_mode = self.display_mode | LCD_ENTRYLEFT
        self.command(LCD_ENTRYMODESET | self.display_mode)

    def right_to_left(self):
        self.display_mode = self.display_mode & (~LCD_ENTRYLEFT | 0xff)
        self.command(LCD_ENTRYMODESET | self.display_mode)

    def autoscroll(self):
        self.display_mode = self.display_mode | LCD_ENTRYSHIFTINCREMENT
        self.command(LCD_ENTRYMODESET | self.display_mode)

    def no_autoscroll(self):
        self.display_mode = self.display_mode | (~LCD_ENTRYSHIFTINCREMENT & 0xff)
        self.command(LCD_ENTRYMODESET | self.display_mode)

    def create_char(self, location, charmap):
        location = location & 0x07
        self.command(LCD_SETCGRAMADDR | (location << 3))
        for i in range(8):
            self.write(charmap[i])

    def command(self, value):
        self.send(value, 0)

    def write(self, value):
        self.send(value, 1)

    def send(self, value, mode):
        self.board.digital_write(self.rs_pin, mode)

        self.write4bits(value >> 4)
        self.write4bits(value)

    def pulse_enable(self):
        self.board.digital_write(self.e_pin, 0)
        time.sleep(0.000001)
        self.board.digital_write(self.e_pin, 1)
        time.sleep(0.000001)
        self.board.digital_write(self.e_pin, 0)
        time.sleep(0.0001)

    def write4bits(self, value):
        for i in range(4):
            self.board.digital_write(self.data_pins[i], (value >> i) & 0x01)
        self.pulse_enable()

    def print(self, text):
        for char in text:
            self.write(ord(char))
            # self.scroll_display_left()

    def print_char(self, char):
        self.write(ord(char))

