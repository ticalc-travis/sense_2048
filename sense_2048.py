#!/usr/bin/env python3

import random
import time

import numpy as np
from sense_hat import sense_hat


TILE_EMPTY = 0


TILE_COLORS = {
    TILE_EMPTY: (0, 0, 0),
    2: (255, 255, 255),
    4: (255, 255, 0),
    8: (255, 127, 0),
    16: (255, 0, 0),
    32: (255, 0, 255),
    64: (127, 0, 255),
    128: (0, 0, 255),
    256: (0, 255, 255),
    512: (0, 255, 127),
    1024: (0, 255, 0),
    2048: (0, 127, 0),
}


ROTATIONS = {
    'left': 0,
    'up': 1,
    'right': 2,
    'down': 3,
}


class Board:

    size = 4

    new_tile_vals = [2, 4]

    def __init__(self):
        self._tiles = np.full((self.size, self.size), TILE_EMPTY)
        self.place_tile()

    @property
    def tiles(self):
        return self._tiles.copy()

    def place_tile(self):
        new_tile = random.choice(self.new_tile_vals)
        try:
            coord = tuple(random.choice(np.argwhere(self._tiles == TILE_EMPTY)))
        except IndexError:
            pass
        else:
            self._tiles[coord] = new_tile

    def shift(self, direction):
        tiles = np.rot90(self._tiles, ROTATIONS[direction])
        for i, row in enumerate(tiles):
            tiles[i] = np.concatenate(
                (row[row != TILE_EMPTY], row[row == TILE_EMPTY])
            )
        self._tiles = np.rot90(tiles, -ROTATIONS[direction])

    def merge(self, direction):
        tiles = np.rot90(self._tiles, ROTATIONS[direction])
        for row in tiles:
            for i in range(len(row) - 1):
                if row[i] == row[i+1] and row[i] != TILE_EMPTY:
                    row[i] *= 2
                    row[i+1] = TILE_EMPTY
        self._tiles = np.rot90(tiles, -ROTATIONS[direction])


class UI:

    shift_animation_rate = 1 / 60

    fade_animation_rate = 1 / 60

    fade_animation_steps = 8
    
    def __init__(self, sense_hat, board):
        self._sense_hat = sense_hat
        self._board = board
        self.show_board()

    def _rendered_board(self, tiles):
        scaled = tiles.repeat(2, axis=0).repeat(2, axis=1)
        return np.array(
            [[TILE_COLORS[tile] for tile in row] for row in scaled],
            dtype=np.uint8)

    def _get_display(self):
        return np.reshape(
            np.array(self._sense_hat.get_pixels()), (8, 8, 3)
        ).astype(np.uint8)

    def _set_display(self, pixel_array):
        self._sense_hat.set_pixels(
            [tuple(pixel) for row in pixel_array for pixel in row]
        )

    def show_board(self):
        self._fade_to(self._rendered_board(self._board.tiles))

    def shift(self, direction):
        # Shift board tiles in the requested direction
        self._animate_shift(direction)
        self._board.shift(direction)

        # Merge any matching tiles and animate if anything changed
        orig_tiles = self._board.tiles
        self._board.merge(direction)
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
        display = self._get_display()
        while True:
            rotated_display = np.rot90(display.copy(), ROTATIONS[direction])

            for row in rotated_display:
                for j in range(len(row) - 1):
                    if np.array_equal(row[j], TILE_COLORS[TILE_EMPTY]):
                        row[[j, j+1]] = row[[j+1, j]]

            new_display = np.rot90(rotated_display, -ROTATIONS[direction])
            if np.array_equal(new_display, display):
                break

            self._set_display(new_display)
            display = new_display
            time.sleep(self.shift_animation_rate)

    def _animate_changed(self, old_tiles, new_tiles):
        old_display = self._rendered_board(old_tiles)
        faded_display = self._rendered_board(
            (old_tiles == new_tiles) * old_tiles
        )
        new_display = self._rendered_board(new_tiles)
        self._fade_to(faded_display)
        self._fade_to(new_display)

    def _fade_to(self, new_display):
        orig_display = self._get_display()
        for step in range(self.fade_animation_steps):
            new_display_opacity = (step + 1) / self.fade_animation_steps
            display = np.rint(
                orig_display * (1 - new_display_opacity)
                 + new_display * new_display_opacity
            ).astype(np.uint8)
            self._set_display(display)
            time.sleep(self.fade_animation_rate)

    def get_input(self):
        while True:
            event = self._sense_hat.stick.wait_for_event()
            if event.action == 'pressed':
                if event.direction in ['left', 'right', 'up', 'down']:
                    return event.direction
                if event.direction == 'middle':
                    self._sense_hat.low_light = not self._sense_hat.low_light
        

if __name__ == '__main__':
    board = Board()
    hat = sense_hat.SenseHat()
    ui = UI(hat, board)
    while True:
        direction = ui.get_input()
        ui.shift(direction)
