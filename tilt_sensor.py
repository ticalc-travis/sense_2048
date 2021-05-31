#!/usr/bin/env python3

import collections
import time

from sense_hat import SenseHat


class TiltSensor:

    def __init__(self, hat, sensitivity=0.3, hysteresis=0.15, debounce_delay=15):
        self._hat = hat
        self.sensitivity = sensitivity
        self.hysteresis = hysteresis
        self.debounce_delay = debounce_delay

    def sense_loop(self):
        directions = {
            'x': {'low': 'left', 'high': 'right'},
            'y': {'low': 'up', 'high': 'down'},
        }
        last_stable_tilt = {'x': None, 'y': None}
        last_tilt = last_stable_tilt.copy()
        this_tilt = last_stable_tilt.copy()
        stable_count = {'x': 0, 'y': 0}

        while True:
            accel = self._hat.get_accelerometer_raw()

            for axis in ('x', 'y'):
                if accel[axis] > self.sensitivity:
                    this_tilt[axis] = directions[axis]['high']
                elif accel[axis] < -self.sensitivity:
                    this_tilt[axis] = directions[axis]['low']
                elif abs(accel[axis]) < self.sensitivity - self.hysteresis:
                    this_tilt[axis] = None

                if this_tilt[axis] == last_tilt[axis]:
                    stable_count[axis] += 1
                else:
                    stable_count[axis] = 0
                    last_tilt[axis] = this_tilt[axis]

                if stable_count[axis] == self.debounce_delay:
                    if last_stable_tilt[axis]:
                        print('{} released'.format(last_stable_tilt[axis]))
                    if this_tilt[axis]:
                        print('{} pressed'.format(this_tilt[axis]))
                    last_stable_tilt[axis] = this_tilt[axis]


if __name__ == '__main__':
    hat = SenseHat()
    ts = TiltSensor(hat)
    ts.sense_loop()
