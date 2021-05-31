#!/usr/bin/env python3

import collections
import time

from sense_hat import SenseHat


class TiltSensor:

    def __init__(self, hat, sensitivity=0.3, hysteresis=0.15):
        self._hat = hat
        self.sensitivity = sensitivity
        self.hysteresis = hysteresis

    def sense_loop(self):
        directions = {
            'x': {'low': 'left', 'high': 'right'},
            'y': {'low': 'up', 'high': 'down'},
        }
        last_tilt = {'x': None, 'y': None}

        while True:
            this_tilt = last_tilt.copy()
            accel = self._hat.get_accelerometer_raw()

            for axis in ('x', 'y'):
                if accel[axis] > self.sensitivity:
                    this_tilt[axis] = directions[axis]['high']
                elif accel[axis] < -self.sensitivity:
                    this_tilt[axis] = directions[axis]['low']
                elif abs(accel[axis]) < self.sensitivity - self.hysteresis:
                    this_tilt[axis] = None

                if last_tilt[axis] != this_tilt[axis]:
                    if last_tilt[axis]:
                        print('{} released'.format(last_tilt[axis]))
                    if this_tilt[axis]:
                        print('{} pressed'.format(this_tilt[axis]))

            last_tilt = this_tilt


if __name__ == '__main__':
    hat = SenseHat()
    ts = TiltSensor(hat)
    ts.sense_loop()
