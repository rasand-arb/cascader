from typing import Annotated
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import math
from pathlib import Path
import logging

# same logging as server
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

### Logic ###
PAGEURL = "127.0.0.1:3002"
NUMBER_OF_COLUMNS = 10
NUMBER_OF_ROWS = 5
NUMBER_OF_BLOCKS = NUMBER_OF_COLUMNS * NUMBER_OF_ROWS
BLOCK_OPTIONS = [
    "amplifier",
    "filter-bp",
    "filter-hp",
    "filter-lp",
    "mixer",
    "oscillator",
]

block_classes = ["block"] * NUMBER_OF_BLOCKS
block_show = block_classes
page = {"url": PAGEURL}


def get_block_coordinates(block_number: int) -> tuple:
    x = block_number % NUMBER_OF_COLUMNS
    y = math.floor(block_number / NUMBER_OF_COLUMNS)
    return x, y


def get_block_number(x: int, y: int) -> int:
    return x + (y * NUMBER_OF_COLUMNS)


def get_selectbox_block_numbers(block_number: int) -> list:
    result = []
    size_box = (3, 3)
    _coords = get_block_coordinates(block_number)
    _x = _coords[0]
    _y = _coords[1]
    for y in range(_y, _y + size_box[1]):
        for x in range(_x, _x + size_box[0]):
            result.append(get_block_number(x, y))
    return result


def show_block_replace(list_block_idx_to_replace: list, list_block_new: list) -> list:
    global block_show
    for idx, new_block in enumerate(list_block_new):
        idx_existing = list_block_idx_to_replace[idx]
        block_show[idx_existing] = new_block


def show_block_revert(list_block_idx_to_revert: list) -> list:
    global block_show
    for block_idx in list_block_idx_to_revert:
        block_show[block_idx] = block_classes[block_idx]
    return block_show


# FastAPI config
app = FastAPI()
path = Path(__file__).parent
static_path = path / "static"
templates_path = static_path / "templates"

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


### Routes ###


@app.get("/", response_class=HTMLResponse)
def head(request: Request) -> HTMLResponse:
    blocks = [
        {"number": i, "class": block_class}
        for i, block_class in enumerate(block_classes)
    ]
    return templates.TemplateResponse(
        "index.html", {"request": request, "blocks": blocks, "page": page}
    )


@app.get("/block/{block_number}", response_class=HTMLResponse)
def block(request: Request, block_number: int) -> HTMLResponse:
    block_number = int(block_number)
    block = {"number": block_number, "class": block_classes[block_number]}
    return templates.TemplateResponse(
        "block.html", {"request": request, "block": block, "page": page}
    )


@app.post("/block/selectbox/{block_number}", response_class=HTMLResponse)
def block_selectbox(request: Request, block_number: int) -> HTMLResponse:
    block_number = int(block_number)
    list_block_idx_to_replace = get_selectbox_block_numbers(block_number)
    list_block_new = BLOCK_OPTIONS
    show_block_replace(list_block_idx_to_replace, list_block_new)
    blocks = [
        {"number": i, "class": block_class} for i, block_class in enumerate(block_show)
    ]
    return templates.TemplateResponse(
        "canvas.html", {"request": request, "blocks": blocks, "page": page}
    )


if __name__ == "__main__":
    print(get_block_coordinates(1))
    print(get_block_number(9, 4))
    print(block_classes[0])
    print(block_classes[49])
    print(get_selectbox_block_numbers(2))
