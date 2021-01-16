from typing import List

from game_message import GameMessage, Position, Crew, TileType, UnitType
from game_command import Action, UnitAction, UnitActionType, BuyAction

import random


class Bot:

    def __init__(self):
        self.my_crew = None
        self.crews = None
        self.game_map = None
        self.rules = None
        self.my_id = None
        self.my_crew = None
        self.blitzium = None
        self.units = None
        self.MAX_MINER_AMOUNT = 5
        self.MAX_CART_AMOUNT = 5



    def get_next_move(self, game_message: GameMessage) -> List[Action]:

        self.my_crew: Crew = game_message.get_crews_by_id()[game_message.crewId]
        self.crews = game_message.crews
        self.game_map = game_message.map
        self.rules = game_message.rules
        self.my_id = game_message.crewId
        self.blitzium = self.my_crew.blitzium
        self.units = self.my_crew.units


        actions: List[Action] = [self.get_miner_action(unit) for unit in self.units if
                                 unit.type == UnitType.MINER]

        cart_actions: List[Action] = [self.get_cart_action(unit) for unit in
                                      self.units if unit.type == UnitType.CART]
        actions.extend(cart_actions)
        if game_message.tick == 0:
            actions += [BuyAction(UnitType.CART)]

        if (self.blitzium >= self.my_crew.prices.CART and len(
                list(filter(lambda unit: unit.type == UnitType.CART, self.units))) < self.MAX_CART_AMOUNT and len(
                list(filter(lambda unit: unit.type == UnitType.MINER, self.units))) == self.MAX_MINER_AMOUNT):
            actions.append(BuyAction(UnitType.CART))
        if self.should_buy_miner():
            actions.append(BuyAction(UnitType.MINER))

        return actions

    def get_random_position(self, map_size: int) -> Position:
        return Position(random.randint(0, map_size - 1), random.randint(0, map_size - 1))

    def get_closest_position(self, initial_position, potential_list):
        closest_point = None
        closest_point_distance = 100000000
        for position in potential_list:
            distance = (position.x - initial_position.x) ** 2 + (position.y - initial_position.y) ** 2
            if distance <= closest_point_distance:
                closest_point = Position(position.x, position.y)
                closest_point_distance = distance
        return closest_point

    def get_closest_minable_square(self, init_position):
        minables = []
        for x in range(self.game_map.get_map_size()):
            for y in range(self.game_map.get_map_size()):
                position = Position(x, y)
                if self.game_map.get_tile_type_at(position) == TileType.MINE:
                    adjacents = self.get_adjacent_positions(position)
                    for adjacent in adjacents:
                        if self.position_is_free(adjacent):
                            minables.append(adjacent)
        return self.get_closest_position(init_position, minables)

    def get_adjacent_positions(self, position):
        return [Position(position.x, position.y + 1),
                Position(position.x - 1, position.y),
                Position(position.x, position.y - 1),
                Position(position.x + 1, position.y)]

    def position_is_free(self, position):
        if self.is_in_enemy_zone(position):
            return False

        for crew in self.crews:
            for unit in crew.units:
                if unit.position == position:
                    return False
        try:
            self.game_map.validate_tile_exists(position)
        except:
            return False

        return self.game_map.get_tile_type_at(position) == TileType.EMPTY

    def get_miner_action(self, unit):
        if unit.blitzium >= self.rules.MAX_CART_CARGO:
            return self.drop_miner_cargo(unit)

        for adjacent in self.get_adjacent_positions(unit.position):
            try:
                if self.game_map.get_tile_type_at(adjacent) == TileType.MINE:
                    return UnitAction(UnitActionType.MINE, unit.id, adjacent)
            except:
                pass

        minable = self.get_closest_minable_square(unit.position)
        target = minable if minable is not None else self.get_random_position(self.game_map.get_map_size())
        return UnitAction(UnitActionType.MOVE, unit.id, target)

    def get_cart_action(self, unit):
        if unit.blitzium == self.rules.MAX_CART_CARGO:
            return self.drop_home(unit)

        depot_positions = []
        for depot in self.game_map.depots:
            depot_positions.append(depot.position)

        for adjacent in self.get_adjacent_positions(unit.position):
            try:
                if adjacent in depot_positions:
                    return UnitAction(UnitActionType.PICKUP, unit.id, adjacent)
            except:
                pass

        target = None
        closest_depot = self.get_closest_position(unit.position, depot_positions)

        if closest_depot is not None:
            for adj in self.get_adjacent_positions(closest_depot):
                if self.position_is_free(adj):
                    return UnitAction(UnitActionType.MOVE, unit.id, adj)

        closest_miner_position = self.get_closest_friendly_miner(unit.position)

        return UnitAction(UnitActionType.MOVE, unit.id, closest_miner_position)

    def get_closest_friendly_miner(self, initial_position):
        miner_positions = []
        for unit in self.units:
            if unit.type == UnitType.MINER:
                miner_positions.append(unit.position)
        if miner_positions is not []:
            closest_miner = self.get_closest_position(initial_position, miner_positions)
            adjacents = self.get_adjacent_positions(closest_miner)
            for adjacent in adjacents:
                if self.position_is_free(adjacent):
                    return adjacent
        return self.get_random_position(self.game_map.get_map_size())

    def drop_home(self, unit):
        if self.my_crew.homeBase in self.get_adjacent_positions(unit.position):
            return UnitAction(UnitActionType.DROP, unit.id, self.my_crew.homeBase)

        for adj in self.get_adjacent_positions(self.my_crew.homeBase):
            if self.position_is_free(adj):
                return UnitAction(UnitActionType.MOVE, unit.id, adj)

    def drop_miner_cargo(self, unit):
        for adj in self.get_adjacent_positions(unit.position):
            if self.position_is_free(adj):
                return UnitAction(UnitActionType.DROP, unit.id, adj)

    def is_in_enemy_zone(self, position):
        for crew in self.crews:
            if crew.id == self.my_id:
                continue
            if crew.homeBase.x - 3 <= position.x <= crew.homeBase.x + 3 \
                    and crew.homeBase.y - 3 <= position.y <= crew.homeBase.y + 3:
                return True
        return False

    def get_units_by_type(self, t):
        return list(filter(lambda unit: unit.type == t, self.units))

    def should_buy_miner(self):
        has_cash = self.blitzium >= self.my_crew.prices.MINER
        maxed_out = len(self.get_units_by_type(UnitType.MINER)) >= self.MAX_MINER_AMOUNT
        has_more_spots = self.get_closest_minable_square(self.my_crew.homeBase)
        return has_cash and has_more_spots #and (not maxed_out)