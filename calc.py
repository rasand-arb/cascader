import math

def get_block_number(x: int, y: int, n_columns) -> int:
    return x + (y * n_columns)

def get_block_coordinates(block_number: int, n_columns) -> tuple:
    x = block_number % n_columns
    y = math.floor(block_number / n_columns)
    return x, y

def get_selectbox_block_numbers(block_number: int, n_columns, n_models) -> list:
    result = []
    grid_size = math.ceil(n_models / 3)
    size_box = (3, grid_size)
    _coords = get_block_coordinates(block_number, n_columns)
    _x = _coords[0]
    _y = _coords[1]
    for y in range(_y, _y + size_box[1]):
        for x in range(_x, _x + size_box[0]):
            result.append(get_block_number(x, y, n_columns))
    return result