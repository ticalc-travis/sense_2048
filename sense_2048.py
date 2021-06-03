#!/usr/bin/env python3

import collections
import random
import time
import sys

import numpy as np
from sense_hat import sense_hat


TILE_EMPTY = 0


TILE_COLORS = {
    TILE_EMPTY: [(0, 0, 0), None],
    2: [(255, 255, 255), None],
    4: [(255, 255, 0), None],
    8: [(255, 127, 0), None],
    16: [(255, 0, 0), None],
    32: [(255, 0, 191), None],
    64: [(127, 0, 255), None],
    128: [(0, 0, 191), None],
    256: [(0, 127, 255), None],
    512: [(0, 255, 255), None],
    1024: [(0, 255, 0), None],

    2048: [(0, 95, 0), (95, 255, 95)],
    4096: [(0, 95, 95), (95, 255, 255)],
    8192: [(0, 0, 95), (95, 95, 255)],
    16384: [(95, 0, 95), (255, 95, 255)],
    32768: [(95, 0, 0), (255, 95, 95)],
    65536: [(95, 95, 0), (255, 255, 95)],
    131072: [(95, 95, 95), (127, 127, 127)],
}


ROTATIONS = {
    'left': 0,
    'up': 1,
    'right': 2,
    'down': 3,
}


def interpolate_color(color_x, color_y, position):
    return np.rint(
        color_x * (1 - position) + color_y * position
    ).astype(np.uint8)


class TileColor:

    dynamic_steps = 30

    def __init__(self, color_def=TILE_COLORS):
        self._colors = {}
        self._init_colors(color_def)
        self._step_gen = self._step_gen_factory()
        self._curr_step = next(self._step_gen)

    def _init_colors(self, color_def):
        for tile, colors in color_def.items():
            color_x, color_y = colors
            if color_y is None:
                color_y = color_x
            self._colors[tile] = {
                'x': np.array(color_x),
                'y': np.array(color_y),
            }

    # TODO: A simple formula would likely suffice instead of a
    # full-blown generator, but I don't have time to figure it out now.
    def _step_gen_factory(self):
        while True:
            for step in range(self.dynamic_steps):
                yield step / self.dynamic_steps
            for step in range(self.dynamic_steps, 0, -1):
                yield step / self.dynamic_steps

    def advance_frame(self):
        self._curr_step = next(self._step_gen)

    def static(self, tile):
        return self._colors[tile]['x']

    def dynamic(self, tile):
        colors = self._colors[tile]
        return interpolate_color(colors['x'], colors['y'], self._curr_step)


tile_color = TileColor()


class Board:
    """Object representing the game board with its tiles.

    Instance properties:

    tiles:  A numpy array representing the tile spaces on the board.
    (This returns a copy; mutation does not affect the instance's idea
    of the board state.)  Tiles are indicated by ints representing the
    tile's face value.  TILE_EMPTY indicates no tile in that space.

    score:  The game's current score, calculated as the sum of the
    values of all tiles created through merging of two matching tiles
    """

    def __init__(self, size=(4, 4), new_tile_vals=(2, 4)):
        """Args:

        size:  Tuple representing the board dimensions (x,y)

        new_tile_vals:  A list of possible tile values that will be
        randomly selected and placed on the board at the beginning of
        each turn
        """
        self._size = size
        self._new_tile_vals = new_tile_vals

        self._tiles = np.full(self._size, TILE_EMPTY)
        self.score = 0
        self._random = random.Random()

        self.place_tile()

    @property
    def tiles(self):
        return self._tiles.copy()

    def place_tile(self):
        """Place a randomly-selected tile in a random vacant space on the board
        if space is available.
        """
        new_tile = self._random.choice(self._new_tile_vals)
        try:
            coord = tuple(self._random.choice(
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
        tiles = np.rot90(self._tiles, ROTATIONS[direction])
        for row in tiles:
            for i in range(len(row) - 1):
                if row[i] == row[i+1] and row[i] != TILE_EMPTY:
                    new_tile = row[i] * 2
                    self.score += new_tile
                    row[i], row[i+1] = new_tile, TILE_EMPTY
        self._tiles = np.rot90(tiles, -ROTATIONS[direction])

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

    def get_state(self):
        """Return an object representing the board and game state that can be
        restored with *set_state()*.
        """
        return {
            'tiles': self.tiles,
            'score': self.score,
            'random': self._random.getstate()
        }

    def set_state(self, state):
        """Restore the internal board/game state with the state object retrieved
        earlier from *get_state()*.
        """
        self._tiles = state['tiles']
        self.score = state['score']
        self._random.setstate(state['random'])


class UI:
    """Handler for the overall user interface, including rendering the game
    board to the Sense HAT LED array, animation, and collecting and
    interpreting user input.


    Class attributes:

    undo_size:  Max number of consecutive moves that can be reversed
    with the Undo command

    joystick_hold_time:  Time in seconds a joystick button must be held
    down to be considered a long-press

    animation_rate:  Seconds to wait after each frame of a visual
    animation effect

    fade_animation_steps:  Number of frames to generate for the
    tile-fade/dissolve effect

    scroll_rate:  Text scroll speed for SenseHAT.show_message()
    """

    undo_size = 4

    joystick_hold_time = .5

    animation_rate = 1 / 60

    fade_animation_steps = 8

    scroll_rate = 1 / 18

    def __init__(self, hat):
        """Args:
        hat:  A SenseHat object
        board:  A Board object
        """
        self._hat = hat

        self.restart()

    def restart(self):
        """Reset the board and start a new game."""
        self._board = Board()
        self._undo_stack = collections.deque(maxlen=self.undo_size)

    def _rendered_board(self, tiles):
        # Return a 3D array of pixels (8 rows, 8 cols, 3 RGB components)
        # representing the game board's tiles

        dim_x, dim_y = tiles.shape
        scaled = tiles.repeat(8 / dim_x, axis=0).repeat(8 / dim_y, axis=1)
        return np.array(
            [[tile_color.dynamic(tile) for tile in row] for row in scaled],
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

    def show_board(self, fade=True):
        """Display current state of game board on the Sense HAT."""
        rendered_board = self._rendered_board(self._board.tiles)
        if fade:
            self._fade_to(rendered_board)
        else:
            self._set_display(rendered_board)

    def player_move(self, direction):
        """Perform, animate, and render a complete move in the given direction
        'up', 'down', 'left', or 'right', shifting and merging tiles and
        placing and displaying a new random one.
        """
        # Store current state in undo history
        self._undo_stack.append(self._board.get_state())

        # Shift board tiles in the requested direction
        self._animate_shift(direction)
        self._board.shift(direction)

        # Merge any matching tiles, animate if anything changed, and
        # display current score on console
        orig_tiles = self._board.tiles
        orig_score = self._board.score
        self._board.merge(direction)
        if not np.array_equal(orig_tiles, self._board.tiles):
            self._animate_changed(orig_tiles, self._board.tiles)
        if self._board.score != orig_score:
            self._print_score()

        # Shift board again to fill in any leftover gaps
        self._animate_shift(direction)
        self._board.shift(direction)

        # Finally, end the turn by placing a random tile on the board
        # and fading it in
        self._board.place_tile()
        self.show_board()

    def _print_score(self):
        print('Your current score: {}'.format(self._board.score),
              end='\r', file=sys.stdout)

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
                    if np.array_equal(row[j], tile_color.dynamic(TILE_EMPTY)):
                        row[[j, j+1]] = row[[j+1, j]]
            new_display = np.rot90(rotated_display, -ROTATIONS[direction])

            # Keep going until no pixels have succeeded in moving any further
            if np.array_equal(new_display, display):
                break

            # Render frame to screen
            tile_color.advance_frame()
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

    def _flash(self, times=2):
        # Briefly flash the screen
        for _ in range(times * 2):
            self._fade_to((255, 255, 255) - self._get_display())

    def _fade_to(self, new_display):
        # Perform a dissolve-type transition from the current HAT display
        # contents to that of pixel array *new_display*.

        orig_display = self._get_display()
        for step in range(self.fade_animation_steps):
            new_display_opacity = (step + 1) / self.fade_animation_steps
            display = interpolate_color(
                orig_display, new_display, new_display_opacity)
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
        'left', 'right', 'undo', 'brightness'
        """
        middle_hold_start = None

        # Purge queue of any accidental joystick inputs made previously
        # before we wait for a fresh input
        self._hat.stick.get_events()

        while True:
            events = self._hat.stick.get_events()
            for event in events:
                if event.action == 'pressed':
                    if event.direction in ['left', 'right', 'up', 'down']:
                        return event.direction
                    if event.direction == 'middle':
                        middle_hold_start = time.time()

                if middle_hold_start is not None and event.direction == 'middle':
                    if (event.action == 'held' and
                         event.timestamp - middle_hold_start > self.joystick_hold_time):
                        middle_hold_start = None
                        return 'undo'
                    elif event.action == 'released':
                        middle_hold_start = None
                        return 'brightness'

            tile_color.advance_frame()
            self.show_board(fade=False)
            time.sleep(self.animation_rate)

    def main(self):
        """Perform input/processing/output loop for main game"""
        while True:
            self.show_board()
            while self._board.has_moves():
                self._handle_input(self.get_input())
            self.game_over()
            self.get_input()
            self.restart()

    def _handle_input(self, input_event):
        if input_event in ['left', 'right', 'up', 'down']:
            self.player_move(input_event)
        elif input_event == 'brightness':
            self._hat.low_light = not self._hat.low_light
        elif input_event == 'undo':
            if self._undo_stack:
                print('\nUndo!', file=sys.stdout)
                self._board.set_state(self._undo_stack.pop())
                self._print_score()
                self.show_board()
            else:
                print("\nCan't undo", file=sys.stdout)
                self._flash(1)

    def game_over(self):
        self._flash()
        time.sleep(1)
        self._fade_dots()

        text_color = tile_color.static(np.max(self._board.tiles))
        print('\n\nGame over! Final score: {}\n\n'.format(self._board.score),
              file=sys.stdout)
        self._hat.show_message('Score: {}'.format(self._board.score),
            text_colour=text_color, scroll_speed=self.scroll_rate)

        self.show_board()


if __name__ == '__main__':
    hat = sense_hat.SenseHat()
    ui = UI(hat)
    try:
        ui.main()
    except KeyboardInterrupt:
        hat.clear()
