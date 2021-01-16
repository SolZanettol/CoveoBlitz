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
        self.current_tick = None
        self.total_ticks = None
        self.outlaws_available = 1
        self.MAX_MINER_AMOUNT = 5
        self.MAX_CART_AMOUNT = 5
        

    def get_next_move(self, game_message: GameMessage) -> List[Action]:
        self.my_crew = game_message.get_crews_by_id()[game_message.crewId]
        self.crews = game_message.crews
        self.game_map = game_message.map
        self.rules = game_message.rules
        self.my_id = game_message.crewId
        self.current_tick = game_message.tick
        self.total_ticks = game_message.totalTick
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

        if self.should_buy_outlaw():
            actions.append(BuyAction(UnitType.OUTLAW))
            self.outlaws_available -= 1
        elif self.should_buy_cart():
            actions.append(BuyAction(UnitType.CART))
        elif self.should_buy_miner():
            actions.append(BuyAction(UnitType.MINER))

        return actions

    def get_random_position(self, map_size: int) -> Position:
        return Position(random.randint(0, map_size - 1), random.randint(0, map_size - 1))

    def get_closest_position(self, initial_position, potential_list):
        closest_point = None
        closest_point_distance = 100000000
        for position in potential_list:
            distance = self.get_manhattan_distance(position, initial_position)
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
        if (len(self.crews) > 2 and self.total_ticks - self.current_tick > 250) or (len(self.crews) == 2 and self.total_ticks - self.current_tick > 200):
            if self.blitzium > 200:
                for adjacent in self.get_adjacent_positions(unit.position):
                        for crew in self.crews :
                            if not self.my_id == crew.id:
                                for other in crew.units:
                                    if other.type == UnitType.MINER:
                                        if adjacent == other.position and not self.is_in_enemy_zone(adjacent):
                                            return UnitAction(UnitActionType.ATTACK, unit.id, adjacent)

        enemy = self.get_victim(unit.position)
        target = enemy if enemy is not None else self.get_random_position(self.game_map.get_map_size())
        return UnitAction(UnitActionType.MOVE, unit.id, target)

    def get_victim(self, init_position):
        enemy_outlaws = self.get_enemy_outlaws()
        enemy_miners = self.get_enemy_miners()
        victims = enemy_outlaws
        if enemy_outlaws == []:
            victims = enemy_miners

        closest = self.get_closest_position(init_position, victims)
        if closest is None:
            return None
        for adj in self.get_adjacent_positions(closest):
            if adj in self.in_range:
                return adj

    def get_enemy_miners(self):
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

    def get_enemy_outlaws(self):
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
            if adj in self.in_range and adj not in [u.position for u in self.units]:
                return UnitAction(UnitActionType.MOVE, unit.id, adj)

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

    def get_units_by_type(self, t):
        return list(filter(lambda unit: unit.type == t, self.units))

    def get_manhattan_distance(self, p1, p2):
        return abs(p1.x - p2.x) + abs(p1.y - p2.y)

    def should_buy_miner(self):
        has_cash = self.blitzium >= self.my_crew.prices.MINER
        maxed_out = len(self.get_units_by_type(UnitType.MINER)) >= self.MAX_MINER_AMOUNT
        has_more_spots = self.get_closest_minable_square(self.my_crew.homeBase)
        have_more_time = self.my_crew.prices.MINER * 3 < (self.total_ticks - self.current_tick)

        return has_cash and has_more_spots and have_more_time #and (not maxed_out)

    def per_tick_value(self, position, value):
        distance = self.get_manhattan_distance(position, self.my_crew.homeBase)
        if not value: return 0
        return (2*distance) / value

    def should_buy_cart(self):
        has_cash = self.blitzium >= self.my_crew.prices.CART
        maxed_out = len(self.get_units_by_type(UnitType.CART)) >= self.MAX_CART_AMOUNT
        have_more_time = self.my_crew.prices.CART * 2 < (self.total_ticks - self.current_tick)
        
        total_drops = sum([depot.blitzium for depot in self.game_map.depots])
        print(total_drops)
        carts_to_clear_sources = 1 if total_drops >= 50 else 0
        print(carts_to_clear_sources)
        # carts_to_clear_sources = sum([self.per_tick_value(source.position, source.blitzium/2) for source in self.game_map.depots if not self.is_in_enemy_zone(source.position)])
        carts_to_clear_miners = sum([self.per_tick_value(source.position, 25) for source in self.get_units_by_type(UnitType.MINER) if not self.is_in_enemy_zone(source.position)])
        targetCarts = carts_to_clear_miners + carts_to_clear_sources

        has_enough_carts = targetCarts < len(self.get_units_by_type(UnitType.CART))

        return has_cash and have_more_time and (not has_enough_carts) #and (not maxed_out)

    def should_buy_outlaw(self):
        if self.outlaws_available > 0:
            if self.blitzium >= 125 + self.my_crew.prices.OUTLAW or (self.blitzium >= self.my_crew.prices.OUTLAW and self.has_challenger()):
                return True
        return False

    def has_challenger(self):
        for crew in self.crews:
            for unit in crew.units:
                if unit.type == UnitType.OUTLAW and crew.id != self.my_id:
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