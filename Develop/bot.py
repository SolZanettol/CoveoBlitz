from typing import List

from game_message import GameMessage, Position, Crew, TileType, UnitType
from game_command import Action, UnitAction, UnitActionType, BuyAction

import random


class Bot:

    def get_next_move(self, game_message: GameMessage) -> List[Action]:
        
        my_crew: Crew = game_message.get_crews_by_id()[game_message.crewId]
        crews = game_message.crews
        game_map = game_message.map
        rules = game_message.rules
        my_id = game_message.crewId
        MAX_MINER_AMOUNT = 4

        actions: List[Action] = [self.get_miner_action(unit, game_map, crews, my_crew, my_id, rules) for unit in my_crew.units]

        if(my_crew.blitzium >= my_crew.prices.MINER and len(list(filter(lambda unit: unit.type == UnitType.MINER, my_crew.units))) < MAX_MINER_AMOUNT) :
            actions.append(BuyAction(UnitType.MINER))

        return actions

    def get_random_position(self, map_size: int) -> Position:
        return Position(random.randint(0, map_size - 1), random.randint(0, map_size - 1))

    def get_closest_position(self, initial_position, potential_list):
        closest_point = Position(0, 0)
        closest_point_distance = 100000000
        for position in potential_list:
            distance = (position.x- initial_position.x)**2 + (position.y- initial_position.y)**2
            if distance <= closest_point_distance:
                closest_point = Position(position.x, position.y)
                closest_point_distance = distance
        return closest_point

    def get_closest_minable_square(self, init_position, map, crews, my_id):
        minables = []
        for x in range(map.get_map_size()):
            for y in range(map.get_map_size()):
                position = Position(x, y)
                if map.get_tile_type_at(position) == TileType.MINE:
                    adjacents = self.get_adjacent_positions(position)
                    for adjacent in adjacents:
                        if self.position_is_free(map, crews, adjacent, my_id):
                            minables.append(adjacent)
        return self.get_closest_position(init_position, minables)

    def get_adjacent_positions(self, position):
        return [Position(position.x, position.y + 1),
                Position(position.x -1, position.y),
                Position(position.x, position.y -1),
                Position(position.x + 1, position.y)]

    def position_is_free(self, map, crews, position, my_id):
        if self.is_in_enemy_zone(position, crews, my_id):
            return False

        for crew in crews:
            for unit in crew.units:
                if unit.position == position:
                    return False
        try:
            map.validate_tile_exists(position)
        except:
            return False

        return map.get_tile_type_at(position) == TileType.EMPTY

    def get_miner_action(self, unit, map, crews, my_crew, my_id, rules):
        if unit.blitzium == rules.MAX_MINER_MOVE_CARGO:
            return self.drop_home(unit, my_crew)

        for adjacent in self.get_adjacent_positions(unit.position):
            try:
                if map.get_tile_type_at(adjacent) == TileType.MINE:
                    return UnitAction(UnitActionType.MINE, unit.id, adjacent)
            except:
                pass

        minable = self.get_closest_minable_square(unit.position, map, crews, my_id)
        target = minable if minable is not None else self.get_random_position(map.get_map_size())
        return UnitAction(UnitActionType.MOVE, unit.id, target)

    def drop_home(self, unit, my_crew):
        if my_crew.homeBase in self.get_adjacent_positions(unit.position):
            return UnitAction(UnitActionType.DROP, unit.id, my_crew.homeBase)

        return UnitAction(UnitActionType.MOVE, unit.id, self.get_adjacent_positions(my_crew.homeBase)[0])

    def is_in_enemy_zone(self, position, crews, my_id):
        for crew in crews:
            if crew.id == my_id:
                continue
            if crew.homeBase.x - 3 <= position.x <= crew.homeBase.x + 3 \
                    and crew.homeBase.y - 3 <= position.y <= crew.homeBase.y + 3:
                return True
        return False





