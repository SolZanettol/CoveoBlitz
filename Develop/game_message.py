from __future__ import annotations

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from enum import Enum
from typing import List, Dict


class TileType(Enum):
    EMPTY = "EMPTY"
    WALL = "WALL"
    MINE = "MINE"
    BASE = "BASE"

    @staticmethod
    def get_tile_type(raw_tile: str) -> TileType:
        for tile_type in TileType:
            if raw_tile == tile_type.value:
                return tile_type
        else:
            raise Exception(f"Tile '{raw_tile}'' is not a valid tile.")


@dataclass_json
@dataclass
class Position:
    x: int
    y: int

@dataclass_json
@dataclass
class Prices:
    MINER: int
    OUTLAW: int
    CART: int

@dataclass_json
@dataclass
class Rules:
    MAX_MINER_CARGO: int
    MAX_CART_CARGO: int
    MAX_MINER_MOVE_CARGO: int

@dataclass_json
@dataclass
class Depot:
    position: Position
    blitzium: int


@dataclass_json
class UnitType(Enum):
    MINER = "MINER"
    CART = "CART"
    OUTLAW = "OUTLAW"


@dataclass_json
@dataclass 
class Map:
    tiles: List[List[str]]
    depots: List[Depot]

    def get_map_size(self):
        return len(self.tiles)

    def validate_tile_exists(self, position: Position):
        if position.x < 0 or position.y < 0 or position.x >= self.get_map_size() or position.y >= self.get_map_size():
            raise Exception("Position out is of map")
    
    def get_raw_tile_value_at(self, position: Position):
        self.validate_tile_exists(position)
        return self.tiles[position.x][position.y]

    def get_tile_type_at(self, position: Position): 
        raw_tile = self.get_raw_tile_value_at(position)
        if raw_tile == "EMPTY":
            return TileType.EMPTY
        elif raw_tile == "WALL":
            return TileType.WALL
        elif raw_tile == "MINE":
            return TileType.MINE
        elif raw_tile == "BASE":
            return TileType.BASE
        else:
            raise Exception("Not a valid tile")


@dataclass_json
@dataclass
class Unit:
    id: str
    type: UnitType
    blitzium: int
    position: Position
    path: List[Position]


@dataclass_json
@dataclass
class Crew:
    id: str
    name: str
    homeBase: Position
    blitzium: int
    totalBlitzium: int
    units: List[Unit]
    errors: List[str]
    prices: Prices


@dataclass_json
@dataclass
class GameMessage:
    tick: int
    totalTick: int
    crewId: str
    crews: List[Crew]
    map: Map
    rules: Rules

    def get_crews_by_id(self) -> Dict[str, Crew]:
        return {crew.id: crew for crew in self.crews}
