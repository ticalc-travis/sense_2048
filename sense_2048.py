import copy
import random


TILE_EMPTY = 0

TILE_COLORS = {
    TILE_EMPTY: (0, 0, 0),
    2: (255, 255, 255),
    4: (255, 255, 127),
    8: (255, 255, 0),
    16: (255, 127, 0),
    32: (255, 0, 0),
}


def transposed(matrix):
    return [
        [row[i] for row in matrix]
        for i in range(len(matrix))
    ]


class Board:
    size = 4
    new_tile_vals = [2, 4]

    def __init__(self):
        self._tiles = [[TILE_EMPTY] * self.size for _ in range(self.size)]

    def __str__(self):
        str_ = []
        for row in self._tiles:
            str_.append(str(row))
        return '\n'.join(str_)

    def get_tiles(self):
        return copy.deepcopy(self._tiles)

    def place_tile(self):
        new_row, new_col = random.choice(self._get_empty_tiles())
        self._tiles[new_row][new_col] = random.choice(self.new_tile_vals)

    def _get_empty_tiles(self):
        empty_tiles = []
        for row_pos, row in enumerate(self._tiles):
            for col_pos, value in enumerate(row):
                if not value:
                    empty_tiles.append((row_pos, col_pos))
        return empty_tiles

    def _transformed_tiles(self, tiles, direction):
        if direction == 'left':
            return [row.copy() for row in tiles]
        if direction == 'right':
            return [list(reversed(row)) for row in tiles]
        if direction == 'up':
            return [row for row in transposed(tiles)]
        if direction == 'down':
            return [list(reversed(row)) for row in transposed(tiles)]
        raise ValueError('Unrecognized direction')

    def _untransformed_tiles(self, tiles, direction):
        # Untransformation works by reapplying the original
        # transformation for all directions except “down”. The “down”
        # transformation applies both transposition and row reversal of
        # the grid, in that order, but in order to correctly reverse
        # this those two operations must be applied in the *opposite*
        # order, hence the special case here.
        if direction == 'down':
            return transposed([list(reversed(row)) for row in tiles])
        return self._transformed_tiles(tiles, direction)

    def shift(self, direction):
        tiles = self._transformed_tiles(self._tiles, direction)
        tiles = [self._shifted_row(row) for row in tiles]
        self._tiles = self._untransformed_tiles(tiles, direction)

    def _shifted_row(self, row):
        row = row.copy()
        while TILE_EMPTY in row:
            row.remove(TILE_EMPTY)
        return row + [TILE_EMPTY] * (self.size - len(row))

    def merge(self, direction):
        tiles = self._transformed_tiles(self._tiles, direction)
        tiles = [self._merged_row(row) for row in tiles]
        self._tiles = self._untransformed_tiles(tiles, direction)

    def _merged_row(self, row):
        row = row.copy()
        for i in range(len(row) - 1):
            if row[i] == row[i+1] and row[i] != TILE_EMPTY:
                row[i] *= 2
                row[i+1] = TILE_EMPTY
        return row

    def move(self, direction):
        self.shift(direction)
        self.merge(direction)
        self.shift(direction)
        self.place_tile()
        print(self, end='\n\n')


def render_board(sense_hat, board):
    def on_screen_tile_coords(origin_x, origin_y):
        yield origin_x, origin_y
        yield origin_x + 1, origin_y
        yield origin_x, origin_y + 1
        yield origin_x + 1, origin_y + 1

    for row_ix, row in enumerate(board.get_tiles()):
        for tile_ix, tile in enumerate(row):
            for x, y in on_screen_tile_coords(tile_ix * 2, row_ix * 2):
                sense_hat.set_pixel(x, y, TILE_COLORS[tile])


board = Board()
for _ in range(8):
    board.place_tile()
print(board, end='\n\n')
board.shift('left')
print(board)
