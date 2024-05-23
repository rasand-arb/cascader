from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi_htmx import htmx, htmx_init
from jinja2 import Template
import logging
from calc import get_selectbox_block_numbers
from pydantic import BaseModel


class BlockType(BaseModel):
    id: int
    type: str = "empty"
    model: str = "block_model"
    css_class: str = "block-default empty"
    hx: str = ""


# TODO
# - add blockgrid to session state
# - add blockgrid to database
# - extend BLOCK_HX to include all possible hx attributes
# - fix refresh() method

BLOCKGRID_COLUMNS = 10
BLOCKGRID_ROWS = 6
NUM_BLOCKS = BLOCKGRID_COLUMNS * BLOCKGRID_ROWS
MODELS = ["amplifier", "filter-bp", "filter-hp",
          "filter-lp", "mixer", "oscillator"]
BLOCK_HX = {
    "default": "",
    "empty": "hx-get=/blockgrid/{{id}}/select hx-swap=outerHTML hx-target=#block-grid",
    "select": "hx-post=/blockgrid/{{id}}/select/{{component}} hx-swap=outerHTML hx-target=#block-grid",
    "component": "",
}

EVENTS = {
    "page_loaded": "page loaded",
    "block_selected": "selection of an empty block to place a component",
    "component_added": "add a component to selected block",
    "component_selected": "selection of a component to edit properties",
    "component_update": "update of a components properties",
    "component_deleted": "delete a component from a block",
}


logging.basicConfig(level=logging.DEBUG)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
htmx_init(templates=Jinja2Templates(directory=Path("static") / "templates"))


class Block(BlockType):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_to_empty()

    def render(self):
        return self.model_dump()

    @staticmethod
    def get_model(model: str):
        with open(Path("static") / "fig" / f"{model}.svg", "r") as f:
            return f.read()

    @staticmethod
    def get_hx(hxtype, parameters):
        template = Template(BLOCK_HX[hxtype])
        return template.render(parameters)

    @staticmethod
    def get_css_class(new_class):
        if new_class != "block-default":
            return f"block-default {new_class}"
        else:
            return new_class

    def update_to_empty(self):
        self.type = "empty"
        self.model = "block_model"
        self.css_class = "block-default empty"
        self.hx = self.get_hx("empty", parameters={"id": self.id})

    def update_to_component(self, model: str):
        self.model = self.get_model(model)
        self.type = "component"
        self.css_class = self.get_css_class(model)
        self.hx = self.get_hx(
            "component", parameters={"id": self.id, "component": model}
        )

    def update_to_select(self, clicked_block_id: int, model: str):
        self.type = "select"
        self.css_class = "block-select"
        self.model = self.get_model(model)
        self.hx = self.get_hx(
            "select", parameters={"id": clicked_block_id, "component": model}
        )

    def update_from_block(self, block: BlockType):
        self.type = block.type
        self.model = block.model
        self.css_class = block.css_class
        self.hx = block.hx


class BlockGridMemory(BaseModel):
    id: str
    blocks: list[Block]
    events: list[dict]
    _listeners: list = []

    def __post_init__(self):
        for block in self.blocks:
            block.update_to_empty()

    def add_listener(self, listener):
        self._listeners.append(listener)

    def update_memory(self, event):
        self.events.append(event)
        logging.debug(f"event: {event}")
        # Update memory based on the event

        # Notify listeners of the change
        for listener in self._listeners:
            listener.on_memory_update(event)

    def get_events(self):
        return self.events


class BlockGrid(BaseModel):
    id: str = "block-grid"
    blocks: list[Block] = []

    def __iter__(self) -> iter:
        return iter(self.blocks)

    def render(self) -> list[dict]:
        return [block.render() for block in self.blocks]

    def refresh_blocks_from(self, blocks: list[Block]) -> None:
        for block in blocks:
            self.blocks[block.id].update_from_block(block)


class PageAction:
    def __init__(self, event_type: str, parameters: dict):
        self.event_type = event_type
        self.parameters = parameters

    def emit(self, memory: BlockGridMemory) -> None:
        memory.update_memory(self.get_event_data())

    def get_event_data(self) -> dict:
        return {"event_type": self.event_type, **self.parameters}


class BlockSelectedListener:
    def __init__(self, memory):
        self.memory = memory

    def on_memory_update(self, event_data) -> None:
        if event_data["event_type"] == "block_selected":
            block_id = event_data["block_id"]
            # Perform actions for block selection
            select_box = self.get_blocks_to_mark(block_id)
            # Emit an event to notify memory
            self.memory.update_memory(
                {
                    "event_type": "selectbox_created",
                    "block_id": block_id,
                    "select_box": select_box,
                }
            )

    @staticmethod
    def get_blocks_to_mark(clicked_block_id: int) -> list[Block]:
        select_box = []
        block_ids_to_mark = get_selectbox_block_numbers(
            clicked_block_id, BLOCKGRID_COLUMNS, len(MODELS)
        )
        for i, mark in enumerate(block_ids_to_mark):
            if i < len(MODELS):
                marked_block = Block(id=mark)
                marked_block.update_to_select(clicked_block_id, MODELS[i])
                select_box.append(marked_block)
        return select_box


class ComponentAddedListener:
    def __init__(self, memory):
        self.memory = memory

    def on_memory_update(self, event_data):
        if event_data["event_type"] == "component_added":
            block_id = event_data["block_id"]
            component = event_data["component"]
            # Perform actions for component creation


memory = BlockGridMemory(
    id="block-grid-memory", blocks=[Block(id=i) for i in range(NUM_BLOCKS)], events=[]
)
logging.debug(f"sample block 5: {memory.blocks[5]}")
grid = BlockGrid(id="block-grid", blocks=memory.blocks)
logging.debug(f"sample block 5: {grid.blocks[5]}")
block_selected_listener = BlockSelectedListener(memory)
component_added_listener = ComponentAddedListener(memory)
memory.add_listener(block_selected_listener)
memory.add_listener(component_added_listener)

# HTML Constructors


def construct_blockgrid(grid: BlockGrid):
    return {
        "blockgrid": grid.render(),
    }


def construct_index(grid):
    return {
        **construct_blockgrid(grid),
    }


# Routes/Endpoints/Views


@app.get("/", response_class=HTMLResponse)
@htmx("index", "index")
async def root_page(request: Request):
    PageAction("page_loaded", {}).emit(memory)
    return construct_index(grid)


@app.get("/blockgrid", response_class=HTMLResponse)
@htmx("blockgrid")
async def get_blockgrid(request: Request):
    PageAction("page_loaded", {}).emit(memory)
    return construct_blockgrid(grid)


@app.get("/blockgrid/{block_id}/select", response_class=HTMLResponse)
@htmx("blockgrid", "index")
async def select_block(request: Request, block_id: int):
    PageAction("block_selected", {"block_id": block_id}).emit(memory)
    return construct_blockgrid(grid)


@app.post("/blockgrid/{block_id}/select/{component}", response_class=HTMLResponse)
@htmx("blockgrid", "index")
async def component_select(request: Request, block_id: int, component: str):
    PageAction("component_added", {"block_id": block_id, "component": component}).emit(
        memory
    )
    return construct_blockgrid(grid)


@app.get("/events")
def get_event_data(request: Request) -> list:
    return memory.events


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="localhost", port=3002,
                log_level="debug", reload=True)
