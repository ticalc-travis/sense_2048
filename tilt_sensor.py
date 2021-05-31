#!/usr/bin/env python3

import collections
import queue
import threading
import time

from sense_hat import SenseHat


InputEvent = collections.namedtuple('InputEvent', ('timestamp', 'direction', 'action'))


class TiltJoystick:
    """A class that senses directional tilting of the HAT and presents it as
    joystick-like input.  Once instantiated, an initial call to the
    *enable* method must be made to start up the sensor input processing
    before input events will be delivered.
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

        self._event_queue = queue.SimpleQueue()
        self._sensing_thread = None
        self._terminate_event = threading.Event()

    def _event_processor(self):
        # This method is intended to be run as a worker thread.  It
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

        while not self._terminate_event.is_set():
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
                        self._event_queue.put(
                            InputEvent(timestamp=time.time(),
                                       direction=last_stable_tilt[axis],
                                       action='released')
                        )
                    if this_tilt[axis]:
                        self._event_queue.put(
                            InputEvent(timestamp=time.time(),
                                       direction=this_tilt[axis],
                                       action='pressed')
                        )
                    last_stable_tilt[axis] = this_tilt[axis]

    def enable(self):
        """Start the background sensor-processing thread and enable reading of
        tilt events.
        """
        if self._sensing_thread is None:
            self._terminate_event.clear()
            self._sensing_thread = threading.Thread(
                target=self._event_processor, daemon=True)
            self._sensing_thread.start()

    def disable(self):
        """Shut down the sensor-processing thread and input event generation.
        """
        self._terminate_event.set()
        if self._sensing_thread is not None:
            self._sensing_thread.join()
            self._sensing_thread = None

    def wait_for_event(self):
        """As with sense_hat's SenseHAT.stick API, wait until a directional
        event via tilt occurs, then return an InputEvent-compatible
        namedtuple.

        Warning:  This call will wait forever if the sensor processing
        thread isn't running.  Be sure that enable() has been called
        first.
        """
        return self._event_queue.get()

    def get_events(self):
        """Return a list of InputEvent tuples representing directional events
        that have occurred since the last call to wait_for_event() or
        get_events().
        """
        event_list = []
        while True:
            try:
                event_list.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return event_list


if __name__ == '__main__':
    hat = SenseHat()
    tj = TiltJoystick(hat)
    tj.enable()
    while True:
        print(tj.wait_for_event())
