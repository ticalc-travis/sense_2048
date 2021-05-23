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
        self._tiles = np.zeros((self.size, self.size), dtype=np.int32) + TILE_EMPTY

    @property
    def tiles(self):
        return self._tiles.copy()

    def place_tile(self):
        new_tile = random.choice(self.new_tile_vals)
        coord = random.choice(np.argwhere(self._tiles == TILE_EMPTY))
        self._tiles[tuple(coord)] = new_tile

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

    def move(self, direction):
        self.shift(direction)
        self.merge(direction)
        self.shift(direction)
        self.place_tile()
        print(self._tiles)


class UI:

    shift_animation_rate = 1 / 20

    fade_animation_rate = 1 / 20

    fade_animation_steps = 8
    
    def __init__(self, sense_hat, board):
        self._sense_hat = sense_hat
        self._board = board

    @staticmethod
    def _pixels_to_array(pixels):
        return np.reshape(np.array(pixels), (8, 8, 3)).astype(np.uint16)

    @staticmethod
    def _array_to_pixels(array):
        return [tuple(pixel) for row in array for pixel in row]

    def _tiles_to_pixels(self, tiles):
        scaled = tiles.repeat(2, axis=0).repeat(2, axis=1)
        return [TILE_COLORS[tile] for row in scaled for tile in row]

    def render_board(self):
        self._sense_hat.set_pixels(self._tiles_to_pixels(self._board.tiles))

    def shift(self, direction):
        self._animate_shift(direction)
        self._board.shift(direction)
        orig_tiles = self._board.tiles.copy()
        self._board.merge(direction)
        if not np.array_equal(orig_tiles, self._board.tiles):
            self._animate_changed(orig_tiles, self._board.tiles)
        self._animate_shift(direction)
        self._board.shift(direction)
        self._board.place_tile()
        self._fade_to(self._pixels_to_array(self._tiles_to_pixels(self._board.tiles)))

    def _animate_shift(self, direction):
        display = self._pixels_to_array(self._sense_hat.get_pixels())
        while True:
            new_display = np.rot90(display.copy(), ROTATIONS[direction])

            for row in new_display:
                for j in range(len(row) - 1):
                    if np.array_equal(row[j], TILE_COLORS[TILE_EMPTY]):
                        row[[j, j+1]] = row[[j+1, j]]

            new_display = np.rot90(new_display, -ROTATIONS[direction])
            if np.array_equal(new_display, display):
                break
            self._sense_hat.set_pixels(
                self._array_to_pixels(new_display))
            time.sleep(self.shift_animation_rate)
            display = new_display

    def _animate_changed(self, old_tiles, new_tiles):
        old_display = self._pixels_to_array(self._tiles_to_pixels(old_tiles))
        faded_display = self._pixels_to_array(self._tiles_to_pixels(
            (old_tiles == new_tiles) * old_tiles
        ))
        new_display = self._pixels_to_array(self._tiles_to_pixels(new_tiles))
        self._fade_to(faded_display)
        self._fade_to(new_display)

    def _fade_to(self, new_display):
        orig_display = self._pixels_to_array(self._sense_hat.get_pixels())
        for step in range(self.fade_animation_steps + 1):
            display = (orig_display * (1 - (step / self.fade_animation_steps)) +
                       new_display * (step / self.fade_animation_steps))
            display = np.rint(display).astype(np.uint16)
            self._sense_hat.set_pixels(self._array_to_pixels(display))
            time.sleep(self.fade_animation_rate)

    def get_input(self):
        while True:
            event = self._sense_hat.stick.wait_for_event()
            if event.action == 'pressed':
                if event.direction in ['left', 'right', 'up', 'down']:
                    return event.direction
                elif event.direction == 'middle':
                    self._sense_hat.low_light = not self._sense_hat.low_light
        

if __name__ == '__main__':
    board = Board()
    hat = sense_hat.SenseHat()
    ui = UI(hat, board)
    board.place_tile()
    ui.render_board()
    while True:
        direction = ui.get_input()
        ui.shift(direction)
