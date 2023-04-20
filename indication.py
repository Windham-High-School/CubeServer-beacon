""" Indicator light control
"""

import neopixel_write
import board
import digitalio
import time

#GRB color bytes for the neopixel
GREEN   = b'\xFF\x00\x00'
RED     = b'\x00\xFF\x00'
BLUE    = b'\x00\x00\xFF'
YELLOW  = b'\xFF\xFF\x00'
OFF     = b'\x00\x00\x00'

# Neopixel power control
neopixel_power = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
neopixel_power.direction = digitalio.Direction.OUTPUT
neopixel_power.value = True #turn on the neopixel power

# Neopixel pin
neopixel_pin = digitalio.DigitalInOut(board.NEOPIXEL)
neopixel_pin.direction = digitalio.Direction.OUTPUT


def set_color(color: bytes):
    """ Set the neopixel to the given color
    """
    neopixel_write.neopixel_write(neopixel_pin, color)

def blink_color(color: bytes):
    """ Blink the neopixel with the given color
    """
    for _ in range(3):
        set_color(color)
        time.sleep(0.1)
        set_color(OFF)
        time.sleep(0.1)
