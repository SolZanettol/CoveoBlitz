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
        self.in_range = None
        self.MAX_MINER_AMOUNT = 5
        self.MAX_CART_AMOUNT = 5
        self.MAX_OUTLAW_AMOUNT = 1

    def get_next_move(self, game_message: GameMessage) -> List[Action]:

        self.my_crew = game_message.get_crews_by_id()[game_message.crewId]
        self.crews = game_message.crews
        self.game_map = game_message.map
        self.rules = game_message.rules
        self.my_id = game_message.crewId
        self.blitzium = self.my_crew.blitzium
        self.units = self.my_crew.units

        # insert quickdraw here
        actions: List[Action] = self.quickdraw()
        if actions:
            return actions

        self.in_range = self.get_in_range(self.my_crew, self.crews, self.game_map)

        miner_actions: List[Action] = [self.get_miner_action(unit) for unit in self.units if
                                       unit.type == UnitType.MINER]
        actions.extend(miner_actions)
        cart_actions: List[Action] = [self.get_cart_action(unit) for unit in
                                      self.units if unit.type == UnitType.CART]
        actions.extend(cart_actions)
        outlaw_actions: List[Action] = [self.get_outlaw_action(unit) for unit in
                                        self.units if unit.type == UnitType.OUTLAW]
        actions.extend(outlaw_actions)
        if game_message.tick == 0:
            actions += [BuyAction(UnitType.CART)]

        if (self.blitzium >= self.my_crew.prices.CART and len(
                list(filter(lambda unit: unit.type == UnitType.CART, self.units))) < self.MAX_CART_AMOUNT and len(
            list(filter(lambda unit: unit.type == UnitType.MINER, self.units))) == self.MAX_MINER_AMOUNT):
            actions.append(BuyAction(UnitType.CART))
        if (self.blitzium >= self.my_crew.prices.MINER and len(
                list(filter(lambda unit: unit.type == UnitType.MINER, self.units))) < self.MAX_MINER_AMOUNT):
            actions.append(BuyAction(UnitType.MINER))

        if(self.blitzium >= 400 and len(
                list(filter(lambda unit: unit.type == UnitType.OUTLAW, self.units))) < self.MAX_OUTLAW_AMOUNT):
            actions.append(BuyAction(UnitType.OUTLAW))

        print(actions)
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
                        if adjacent in self.in_range:
                            minables.append(adjacent)
        return self.get_closest_position(init_position, minables)

    def get_adjacent_positions(self, position):
        return [Position(position.x, position.y + 1),
                Position(position.x - 1, position.y),
                Position(position.x, position.y - 1),
                Position(position.x + 1, position.y)]

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

    def get_outlaw_action(self, unit) :
        if self.blitzium > 600:
            for adjacent in self.get_adjacent_positions(unit.position):
                try:
                    for crew in self.crews :
                        if not self.my_id == crew.id:
                            for other in crew.units:
                                if other.type == UnitType.MINER:
                                    if adjacent == other.position:
                                        return UnitAction(UnitActionType.ATTACK, unit.id, adjacent)
                except:
                    pass

        ennemy = self.get_victim(unit.position)
        target = ennemy if ennemy is not None else self.get_random_position(self.game_map.get_map_size())
        return UnitAction(UnitActionType.MOVE, unit.id, target)

    def get_victim(self, init_position):
        enemy_outlaws = self.get_enemy_outlaws(init_position)
        enemy_miners = self.get_enemy_miners(init_position)
        victims = enemy_outlaws
        if enemy_outlaws == []:
            victims = enemy_miners
        return self.get_closest_position(init_position, victims)
    
    def get_enemy_miners(self, init_position):
        enemy_miners = []
        for x in range(self.game_map.get_map_size()):
            for y in range(self.game_map.get_map_size()):
                position = Position(x, y)
                for crew in self.crews :
                    if not self.my_id == crew.id:
                        for unit in crew.units:
                            if unit.type == UnitType.MINER:
                                if position == unit.position:
                                    adjacents = self.get_adjacent_positions(position)
                                    for adjacent in adjacents:
                                        if adjacent in self.in_range:
                                            enemy_miners.append(adjacent)
        return enemy_miners

    def get_enemy_outlaws(self, init_position):
        enemy_outlaws = []
        for x in range(self.game_map.get_map_size()):
            for y in range(self.game_map.get_map_size()):
                position = Position(x, y)
                for crew in self.crews:
                    if not self.my_id == crew.id:
                        for unit in crew.units:
                            if unit.type == UnitType.OUTLAW:
                                if position == unit.position:
                                    adjacents = self.get_adjacent_positions(position)
                                    for adjacent in adjacents:
                                        if adjacent in self.in_range:
                                            enemy_outlaws.append(adjacent)
        return enemy_outlaws

    def quickdraw(self):
        for unit in self.units:
            if unit.type == UnitType.OUTLAW:
                for adjacent in self.get_adjacent_positions(unit.position):
                    for crew in self.crews:
                        if not self.my_id == crew.id:
                            for other in crew.units:
                                if other.type == UnitType.OUTLAW:
                                    if adjacent == other.position:
                                        return [UnitAction(UnitActionType.ATTACK, unit.id, adjacent)]

        return []


    def get_cart_action(self, unit):
        if unit.blitzium == self.rules.MAX_CART_CARGO:
            return self.drop_home(unit)

        depot_positions_in_range = []
        depot_positions = []
        for depot in self.game_map.depots:
            if depot.position in self.in_range:
                depot_positions_in_range.append(depot.position)
            depot_positions.append(depot.position)

        for adjacent in self.get_adjacent_positions(unit.position):
            if adjacent in depot_positions:
                return UnitAction(UnitActionType.PICKUP, unit.id, adjacent)

        closest_depot = self.get_closest_position(unit.position, depot_positions_in_range)

        if closest_depot is not None:
            for adj in self.get_adjacent_positions(closest_depot):
                if adj in self.in_range:
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
                if adjacent in self.in_range:
                    return adjacent
        return self.get_random_position(self.game_map.get_map_size())

    def drop_home(self, unit):
        if self.my_crew.homeBase in self.get_adjacent_positions(unit.position):
            return UnitAction(UnitActionType.DROP, unit.id, self.my_crew.homeBase)

        for adj in self.get_adjacent_positions(self.my_crew.homeBase):
            if adj in self.in_range:
                return UnitAction(UnitActionType.MOVE, unit.id, adj)

    def drop_miner_cargo(self, unit):
        for adj in self.get_adjacent_positions(unit.position):
            if adj in self.in_range:
                return UnitAction(UnitActionType.DROP, unit.id, adj)

    def is_in_enemy_zone(self, position):
        for crew in self.crews:
            if crew.id == self.my_id:
                continue
            if crew.homeBase.x - 3 <= position.x <= crew.homeBase.x + 3 \
                    and crew.homeBase.y - 3 <= position.y <= crew.homeBase.y + 3:
                return True
        return False

    def get_in_range(self, my_crew, crews, game_map):
        explored = [my_crew.homeBase] + self.get_adjacent_positions(my_crew.homeBase)
        unexplored = self.get_adjacent_positions(my_crew.homeBase)
        in_range = [my_crew.homeBase]

        unit_pos = []
        for crew in crews:
            for unit in crew.units:
                if not unit.path:
                    unit_pos += [unit.position]

        while unexplored:
            exploring, unexplored = unexplored[0], unexplored[1:]


            try:
                self.game_map.validate_tile_exists(exploring)
            except:
                continue

            if game_map.get_tile_type_at(exploring) in [TileType.EMPTY, TileType.BASE]:
                if exploring not in unit_pos and not self.is_in_enemy_zone(exploring):
                    in_range += [exploring]
                    for next in self.get_adjacent_positions(exploring):
                        if next not in explored:
                            explored += [next]
                            unexplored += [next]

        return in_range




