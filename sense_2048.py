import copy
import random


TILE_EMPTY = 0


def transposed(matrix):
    return [
        [row[i] for row in matrix]
        for i in range(len(matrix))
    ]


class Board:
    size = 4
    new_tile_vals = [2, 4]

    def __init__(self):
        self._tiles = [[0] * self.size for _ in range(self.size)]

    def __str__(self):
        str_ = []
        for row in self._tiles:
            str_.append(str(row))
        return '\n'.join(str_)

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
            return self._htransformed(tiles, False)
        if direction == 'right':
            return self._htransformed(tiles, True)
        if direction == 'up':
            return self._vtransformed(tiles, False)
        if direction == 'down':
            return self._vtransformed(tiles, True)
        raise ValueError('Unrecognized direction')

    def _htransformed(self, tiles, reverse):
        return [row.copy() if not reverse else list(reversed(row))
                for row in tiles]

    def _vtransformed(self, tiles, reverse):
        return self._htransformed(transposed(tiles), reverse)


board = Board()
for _ in range(8):
    board.place_tile()
