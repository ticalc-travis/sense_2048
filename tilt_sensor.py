#!/usr/bin/env python3

import collections
import time

from sense_hat import SenseHat


class TiltJoystick:
    """A class that senses directional tilting of the HAT and presents it as
    joystick-like input.
    """

    def __init__(self, hat, sensitivity=0.4, hysteresis=0.2, delay=15):
        """Args:

        hat:  SenseHat object

        sensitivity:  The degree of tilt from horizontal needed to
        trigger a direction “press”, with lower values requiring less of
        a tilt.  A realistic range (assuming normal Earth-gravity
        conditions) is between 0 and 1.

        hysteresis:  The amount of tilting back toward a level position
        from the initial “press” trigger point needed to trigger a
        “release”.

        delay:  The number of frames of stable accelerometer input
        required before a tilt event is accepted as valid.  Higher
        values help filter out false triggers from bumps or shakes but
        reduce response time.
        """
        self._hat = hat
        self.sensitivity = sensitivity
        self.hysteresis = hysteresis
        self.delay = delay

    def _sensing_thread(self):
        # This method is intended to be run as a daemon thread.  It
        # continuously reads the accelerometer and interprets the data,
        # adding directional “press” and “release” inputs to an event
        # queue as they're detected.

        # Mapping of axis and sign of acceleration to cardinal direction
        directions = {
            'x': {'-': 'left', '+': 'right'},
            'y': {'-': 'up', '+': 'down'},
        }

        # Estimated cardinal direction of tilt for each axis (or None
        # for neutral/unknown)
        last_stable_tilt = {'x': None, 'y': None}
        last_tilt = last_stable_tilt.copy()
        this_tilt = last_stable_tilt.copy()

        stable_count = {'x': 0, 'y': 0}

        while True:
            accel = self._hat.get_accelerometer_raw()

            for axis in ('x', 'y'):
                # Estimate instantaneous tilt direction, accounting for
                # hysteresis
                if accel[axis] > self.sensitivity:
                    this_tilt[axis] = directions[axis]['+']
                elif accel[axis] < -self.sensitivity:
                    this_tilt[axis] = directions[axis]['-']
                elif abs(accel[axis]) < self.sensitivity - self.hysteresis:
                    this_tilt[axis] = None

                # Keep track of how long the tilt direction has been
                # stable; if it changed, reset the count of stable
                # frames.
                if this_tilt[axis] == last_tilt[axis]:
                    stable_count[axis] += 1
                else:
                    stable_count[axis] = 0
                    last_tilt[axis] = this_tilt[axis]

                # As soon as a stable direction is determined, add the
                # appropriate “joystick” events to the queue
                if stable_count[axis] == self.delay:
                    if last_stable_tilt[axis]:
                        print('{} released'.format(last_stable_tilt[axis]))
                    if this_tilt[axis]:
                        print('{} pressed'.format(this_tilt[axis]))
                    last_stable_tilt[axis] = this_tilt[axis]


if __name__ == '__main__':
    hat = SenseHat()
    ts = TiltSensor(hat)
    ts.sense_loop()
