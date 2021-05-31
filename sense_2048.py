#!/usr/bin/env python3

import queue
import random
import threading
import time

import numpy as np
import sense_hat


TILE_EMPTY = 0


TILE_COLORS = {
    TILE_EMPTY: (0, 0, 0),
    2: (255, 255, 255),
    4: (255, 255, 0),
    8: (255, 127, 0),
    16: (255, 0, 0),
    32: (255, 0, 191),
    64: (127, 0, 255),
    128: (0, 0, 191),
    256: (0, 127, 255),
    512: (0, 255, 255),
    1024: (0, 255, 0),
    2048: (0, 95, 0),
}


ROTATIONS = {
    'left': 0,
    'up': 1,
    'right': 2,
    'down': 3,
}


class Board:
    """Object representing the game board with its tiles.

    Instance properties:

    tiles:  A numpy array representing the tile spaces on the board.
    (This returns a copy; mutation does not affect the instance's idea
    of the board state.)  Tiles are indicated by ints representing the
    tile's face value.  TILE_EMPTY indicates no tile in that space.
    """

    def __init__(self, size=4, new_tile_vals=(2, 4)):
        """Args:

        size:  Number of tiles across each dimension of the board

        new_tile_vals:  A list of possible tile values that will be
        randomly selected and placed on the board at the beginning of
        each turn
        """
        self._size = size
        self._new_tile_vals = new_tile_vals

        self._tiles = np.full((self._size, self._size), TILE_EMPTY)
        self.place_tile()

    @property
    def tiles(self):
        return self._tiles.copy()

    def place_tile(self):
        """Place a randomly-selected tile in a random vacant space on the board
        if space is available.
        """
        new_tile = random.choice(self._new_tile_vals)
        try:
            coord = tuple(random.choice(
                np.argwhere(self._tiles == TILE_EMPTY)))
        except IndexError:
            pass
        else:
            self._tiles[coord] = new_tile

    def shift(self, direction):
        """Shift all tiles in the given direction 'up', 'down', 'left', or
        'right' as far as possible.
        """
        tiles = np.rot90(self._tiles, ROTATIONS[direction])
        for i, row in enumerate(tiles):
            tiles[i] = np.concatenate(
                (row[row != TILE_EMPTY], row[row == TILE_EMPTY])
            )
        self._tiles = np.rot90(tiles, -ROTATIONS[direction])

    def merge(self, direction):
        """Search for pairs of adjacent matching tiles that would bump against
        each other if pushed in the given direction 'up', 'down',
        'left', or 'right'; replace each such pair of tiles with a tile
        of double the original value and an empty space.  Return the
        scoring value of the merges (the sum of all newly created
        tiles).
        """
        score = 0
        tiles = np.rot90(self._tiles, ROTATIONS[direction])
        for row in tiles:
            for i in range(len(row) - 1):
                if row[i] == row[i+1] and row[i] != TILE_EMPTY:
                    new_tile = row[i] * 2
                    score += new_tile
                    row[i], row[i+1] = new_tile, TILE_EMPTY
        self._tiles = np.rot90(tiles, -ROTATIONS[direction])
        return score

    def has_moves(self):
        """Return True if legal moves are possible, False if there are no moves
        left and the game is over.
        """
        # Moving is possible if there are vacant spaces on the board
        if np.any(self._tiles == TILE_EMPTY):
            return True
        # Otherwise, moving is only possible as long as any two adjacent
        # horizontal or vertical tiles match
        return (
            np.any(self._tiles[:, :-1] == self._tiles[:, 1:])     # Horizontal
            or np.any(self._tiles[:-1, :] == self._tiles[1:, :])  # Vertical
        )


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
                            sense_hat.InputEvent(
                                timestamp=time.time(),
                                direction=last_stable_tilt[axis],
                                action='released')
                        )
                    if this_tilt[axis]:
                        self._event_queue.put(
                            sense_hat.InputEvent(
                                timestamp=time.time(),
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
        event via tilt occurs, then return an InputEvent namedtuple.

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


class UI:
    """Handler for the overall user interface, including rendering the game
    board to the Sense HAT LED array, animation, and collecting and
    interpreting user input.


    Instance attributes:

    score:  Player's current score


    Class attributes:

    animation_rate:  Seconds to wait after each frame of a visual
    animation effect

    fade_animation_steps:  Number of frames to generate for the
    tile-fade/dissolve effect

    scroll_rate:  Text scroll speed for SenseHAT.show_message()
    """

    animation_rate = 1 / 60

    fade_animation_steps = 8

    scroll_rate = 1 / 18

    def __init__(self, hat, tilt_joystick=None):
        """Args:

        hat:  A SenseHat object

        tilt_joystick:  An optional TiltJoystick object if tilt control
        support is desired.
        """
        self._hat = hat
        self._tilt = tilt_joystick

        if self._tilt is not None:
            self._tilt.enable()
        self.restart()

    def restart(self):
        """Reset the board and start a new game."""
        self._board = Board()
        self.score = 0

    def _rendered_board(self, tiles):
        # Return a 3D array of pixels (8 rows, 8 cols, 3 RGB components)
        # representing the game board's tiles

        scaled = tiles.repeat(2, axis=0).repeat(2, axis=1)
        return np.array(
            [[TILE_COLORS[tile] for tile in row] for row in scaled],
            dtype=np.uint8)

    def _get_display(self):
        # Retrieve display from Sense HAT, converted to Numpy 8×8×3
        # array

        return np.reshape(
            np.array(self._hat.get_pixels()), (8, 8, 3)
        ).astype(np.uint8)

    def _set_display(self, pixel_array):
        # Send 8×8×3 pixel array to Sense HAT's LED matrix
        self._hat.set_pixels(
            [tuple(pixel) for row in pixel_array for pixel in row]
        )

    def show_board(self):
        """Display current state of game board on the Sense HAT."""
        self._fade_to(self._rendered_board(self._board.tiles))

    def player_move(self, direction):
        """Perform, animate, and render a complete move in the given direction
        'up', 'down', 'left', or 'right', shifting and merging tiles and
        placing and displaying a new random one.
        """
        # Shift board tiles in the requested direction
        self._animate_shift(direction)
        self._board.shift(direction)

        # Merge any matching tiles and animate if anything changed
        orig_tiles = self._board.tiles
        self.score += self._board.merge(direction)
        if not np.array_equal(orig_tiles, self._board.tiles):
            self._animate_changed(orig_tiles, self._board.tiles)

        # Shift board again to fill in any leftover gaps
        self._animate_shift(direction)
        self._board.shift(direction)

        # Finally, end the turn by placing a random tile on the board
        # and fading it in
        self._board.place_tile()
        self.show_board()

    def _animate_shift(self, direction):
        # Visually shift the tiles on the HAT screen in the given
        # direction.  This only affects the display; the underlying
        # Board object should be sent its own shift command in order to
        # ensure its tiles match the resulting screen state.

        display = self._get_display()

        while True:
            # Slide pixels representing tiles over by one wherever there
            # are empty pixels to slide into
            rotated_display = np.rot90(display.copy(), ROTATIONS[direction])
            for row in rotated_display:
                for j in range(len(row) - 1):
                    if np.array_equal(row[j], TILE_COLORS[TILE_EMPTY]):
                        row[[j, j+1]] = row[[j+1, j]]
            new_display = np.rot90(rotated_display, -ROTATIONS[direction])

            # Keep going until no pixels have succeeded in moving any further
            if np.array_equal(new_display, display):
                break

            # Render frame to screen
            self._set_display(new_display)
            display = new_display
            time.sleep(self.animation_rate)

    def _animate_changed(self, old_tiles, new_tiles):
        # Given two arrays of board tiles, render a fade-out effect for
        # the on-screen tiles that have changed between the arrays, then
        # fade in the new tiles from new_tiles.

        old_display = self._rendered_board(old_tiles)
        faded_display = self._rendered_board(
            (old_tiles == new_tiles) * old_tiles
        )
        new_display = self._rendered_board(new_tiles)

        self._fade_to(faded_display)
        self._fade_to(new_display)

    def _flash(self):
        # Briefly flash the screen
        for _ in range(4):
            self._fade_to((255, 255, 255) - self._get_display())

    def _fade_to(self, new_display):
        # Perform a dissolve-type transition from the current HAT display
        # contents to that of pixel array *new_display*.

        orig_display = self._get_display()
        for step in range(self.fade_animation_steps):
            new_display_opacity = (step + 1) / self.fade_animation_steps
            display = np.rint(
                orig_display * (1 - new_display_opacity)
                 + new_display * new_display_opacity
            ).astype(np.uint8)
            self._set_display(display)
            time.sleep(self.animation_rate)

    def _fade_dots(self):
        # Turn off all pixels on the HAT in a shuffled sequence
        coords = list([(x // 8, x % 8) for x in range(64)])
        random.shuffle(coords)
        for coord in coords:
            self._hat.set_pixel(*coord, (0, 0, 0))
            time.sleep(self.animation_rate)

    def get_input(self):
        """Wait for an input event and return it as a string: 'up, 'down',
        'left', 'right'
        """
        # Purge queue of any accidental joystick inputs made previously
        # before we wait for a fresh input
        self._hat.stick.get_events()
        if self._tilt is not None:
            self._tilt.get_events()

        while True:
            events = self._hat.stick.get_events()
            if self._tilt is not None:
                events += self._tilt.get_events()
            for event in events:
                if event.action == 'pressed':
                    if event.direction in ['left', 'right', 'up', 'down']:
                        return event.direction
                    if event.direction == 'middle':
                        self._hat.low_light = not self._hat.low_light
            time.sleep(self.animation_rate)

    def main(self):
        """Perform input/processing/output loop for main game"""
        while True:
            self.show_board()
            while self._board.has_moves():
                direction = self.get_input()
                self.player_move(direction)
            self.game_over()
            self.get_input()
            self.restart()

    def game_over(self):
        self._flash()
        time.sleep(1)
        self._fade_dots()

        text_color = TILE_COLORS[np.max(self._board.tiles)]
        message = 'Game over! Score: {}'.format(self.score)
        print(message)
        self._hat.show_message(
            message, text_colour=text_color, scroll_speed=self.scroll_rate)

        self.show_board()


if __name__ == '__main__':
    hat = sense_hat.SenseHat()
    tilt_joystick = TiltJoystick(hat)
    ui = UI(hat, tilt_joystick)
    try:
        ui.main()
    except KeyboardInterrupt:
        hat.clear()
