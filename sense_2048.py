import random

import numpy as np


TILE_EMPTY = 0

TILE_COLORS = {
    TILE_EMPTY: (0, 0, 0),
    2: (255, 255, 255),
    4: (255, 255, 127),
    8: (255, 255, 0),
    16: (255, 127, 0),
    32: (255, 0, 0),
}


class Board:

    size = 4

    new_tile_vals = [2, 4]

    rotations = {
        'left': 0,
        'up': 1,
        'right': 2,
        'down': 3,
    }

    def __init__(self):
        self._tiles = np.zeros((self.size, self.size), dtype=np.int32) + TILE_EMPTY

    @property
    def tiles(self):
        return self._tiles

    def place_tile(self):
        new_tile = random.choice(self.new_tile_vals)
        coord = random.choice(np.argwhere(self._tiles == TILE_EMPTY))
        self._tiles[tuple(coord)] = new_tile

    def shift(self, direction):
        tiles = np.rot90(self._tiles, self.rotations[direction])
        for i, row in enumerate(tiles):
            tiles[i] = np.concatenate(
                (row[row != TILE_EMPTY], row[row == TILE_EMPTY])
            )
        self._tiles = np.rot90(tiles, -self.rotations[direction])

    def merge(self, direction):
        tiles = np.rot90(self._tiles, self.rotations[direction])
        for row in tiles:
            for i in range(len(row) - 1):
                if row[i] == row[i+1] and row[i] != TILE_EMPTY:
                    row[i] *= 2
                    row[i+1] = TILE_EMPTY
        self._tiles = np.rot90(tiles, -self.rotations[direction])

    def move(self, direction):
        self.shift(direction)
        self.merge(direction)
        self.shift(direction)
        self.place_tile()
        print(self._tiles)


def render_board(sense_hat, board):
    def on_screen_tile_coords(origin_x, origin_y):
        yield origin_x, origin_y
        yield origin_x + 1, origin_y
        yield origin_x, origin_y + 1
        yield origin_x + 1, origin_y + 1

    for row_ix, row in enumerate(board.tiles):
        for tile_ix, tile in enumerate(row):
            for x, y in on_screen_tile_coords(tile_ix * 2, row_ix * 2):
                sense_hat.set_pixel(x, y, TILE_COLORS[tile])


board = Board()
for _ in range(8):
    board.place_tile()
print(board.tiles)
board.shift('left')
print(board.tiles)
