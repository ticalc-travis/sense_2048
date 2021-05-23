import random
import time

import numpy as np
from sense_emu import sense_hat


TILE_EMPTY = 0

TILE_COLORS = {
    TILE_EMPTY: (0, 0, 0),
    2: (255, 255, 255),
    4: (255, 255, 127),
    8: (255, 255, 0),
    16: (255, 127, 0),
    32: (255, 0, 0),
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

    shift_animation_rate = 0.05
    
    def __init__(self, sense_hat, board):
        self._sense_hat = sense_hat
        self._board = board

    def render_board(self):
        scaled = self._board.tiles.repeat(2, axis=0).repeat(2, axis=1)
        pixels = [TILE_COLORS[tile] for row in scaled for tile in row]
        self._sense_hat.set_pixels(pixels)

    def shift(self, direction):
        self._animate_shift(direction)
        self._board.shift(direction)

    def _animate_shift(self, direction):
        display = np.reshape(
            np.array(self._sense_hat.get_pixels()), (8, 8, 3)
        )
        while True:
            new_display = np.rot90(display.copy(), ROTATIONS[direction])

            for row in new_display:
                for j in range(len(row) - 1):
                    if np.array_equal(row[j], TILE_COLORS[TILE_EMPTY]):
                        row[[j, j+1]] = row[[j+1, j]]

            new_display = np.rot90(new_display, -ROTATIONS[direction])
            print(display)
            print(new_display)
            if np.array_equal(new_display, display):
                break
            self._sense_hat.set_pixels(
                [tuple(pixel) for row in new_display for pixel in row])
            time.sleep(self.shift_animation_rate)
            display = new_display
    

if __name__ == '__main__':
    board = Board()
    hat = sense_hat.SenseHat()
    ui = UI(hat, board)
    board.place_tile()
    ui.render_board()
    
