from typing import List

from game_message import GameMessage, Position, Crew, TileType, UnitType
from game_command import Action, UnitAction, UnitActionType, BuyAction

import random
import numpy as np
import cv2

import itertools


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
        self.mine_dispatched = {}
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

    def get_minable_squares(self):
        minables = []
        for x in range(self.game_map.get_map_size()):
            for y in range(self.game_map.get_map_size()):
                position = Position(x, y)
                if self.game_map.get_tile_type_at(position) == TileType.MINE:
                    adjacents = self.get_adjacent_positions(position)
                    for adjacent in adjacents:
                        if adjacent in self.in_range:
                            minables.append(adjacent)
        return minables

    def get_closest_minable_square(self, init_position):
        return self.get_closest_position(init_position, self.get_minable_squares())

    def get_adjacent_positions(self, position):
        return [Position(position.x, position.y + 1),
                Position(position.x - 1, position.y),
                Position(position.x, position.y - 1),
                Position(position.x + 1, position.y)]

    def get_miner_action(self, unit):
        if unit.blitzium >= 40:
            return self.drop_miner_cargo(unit)

        for adjacent in self.get_adjacent_positions(unit.position):
            if self.game_map.get_tile_type_at(adjacent) == TileType.MINE:
                return UnitAction(UnitActionType.MINE, unit.id, adjacent)

        minable = self.get_closest_minable_square(unit.position)
        target = minable if minable is not None else self.get_random_position(self.game_map.get_map_size())
        return UnitAction(UnitActionType.MOVE, unit.id, target)

    def get_outlaw_action(self, unit) :
        if len(self.crews) == 2:    
            if (self.total_ticks - self.current_tick > 300):
                if self.blitzium > 200:
                    for adjacent in self.get_adjacent_positions(unit.position):
                            for crew in self.crews :
                                if not self.my_id == crew.id:
                                    for other in crew.units:
                                        if other.type == UnitType.MINER:
                                            if adjacent == other.position and not self.is_in_enemy_zone(adjacent):
                                                return UnitAction(UnitActionType.ATTACK, unit.id, adjacent)
        enemy = self.get_victim(unit.position)
        if enemy is not None:
            return UnitAction(UnitActionType.MOVE, unit.id, enemy)
        else:
            return UnitAction(UnitActionType.MOVE, unit.id, self.get_random_position(self.game_map.get_map_size()))

    def get_victim(self, init_position):
        enemy_outlaws = self.get_enemy_outlaws()
        enemy_miners = self.get_enemy_miners()
        victims = enemy_outlaws
        if enemy_outlaws == []:
            if len(self.crews) == 2:
                if len(enemy_miners) > 1:
                    victims = enemy_miners

        closest = self.get_closest_position(init_position, victims)
        if closest is None:
            return None
        else:
            return closest

    def get_enemy_miners(self):
        enemy_miners = []
        for x in range(self.game_map.get_map_size()):
            for y in range(self.game_map.get_map_size()):
                position = Position(x, y)
                for crew in self.crews :
                    if not self.my_id == crew.id:
                        for unit in crew.units:
                            if unit.type == UnitType.MINER:
                                if position == unit.position and not self.is_in_enemy_zone(position):
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
                            if unit.type == UnitType.OUTLAW and self.blitzium > 50:
                                if position == unit.position:
                                    adjacents = self.get_adjacent_positions(position)
                                    for adjacent in adjacents:
                                        if adjacent in self.in_range:
                                            enemy_outlaws.append(adjacent)
        return enemy_outlaws

    def quickdraw(self):
        for unit in self.units:
            if unit.type == UnitType.OUTLAW:
                for adjacent, crew in itertools.product(self.get_adjacent_positions(unit.position), self.crews):
                    if not self.my_id == crew.id:
                        for other in crew.units:
                            if other.type == UnitType.OUTLAW and self.blitzium > 50 and adjacent == other.position:
                                if adjacent == other.position:
                                    return [UnitAction(UnitActionType.ATTACK, unit.id, adjacent)]

        return []


    def get_cart_action(self, unit):
        if unit.blitzium == self.rules.MAX_CART_CARGO:
            return self.drop_home(unit)

        if unit.blitzium == 0:
            for adjacent, cart in itertools.product(self.get_adjacent_positions(unit.position), self.get_units_by_type(UnitType.CART)):
                if (cart.position == adjacent and
                    self.get_manhattan_distance(adjacent, self.my_crew.homeBase) > self.get_manhattan_distance(unit.position, self.my_crew.homeBase) and
                    cart.blitzium == self.rules.MAX_CART_CARGO):
                    return UnitAction(UnitActionType.PICKUP, unit.id, adjacent)
            if unit.position in self.get_adjacent_positions(self.my_crew.homeBase):
                for adj in self.get_adjacent_positions(unit.position):
                    if adj != self.my_crew.homeBase and adj in self.in_range:
                        return UnitAction(UnitActionType.MOVE, unit.id, adjacent)

        depot_positions_in_range = []
        depot_positions = []
        for depot in self.game_map.depots:
            if depot.position in self.in_range:
                depot_positions_in_range.append(depot.position)
            depot_positions.append(depot.position)

        for adjacent in self.get_adjacent_positions(unit.position):
            if adjacent in depot_positions:
                return UnitAction(UnitActionType.PICKUP, unit.id, adjacent)
            elif adjacent == self.my_crew.homeBase and unit.blitzium != 0:
                return UnitAction(UnitActionType.DROP, unit.id, adjacent)

        closest_depot = self.get_closest_position(unit.position, depot_positions_in_range)

        for adjacent in self.get_adjacent_positions(unit.position):
            for miner in self.get_units_by_type(UnitType.MINER):
                if (adjacent == miner.position and
                    (closest_depot is None or
                    miner.blitzium >= 25)):
                    return UnitAction(UnitActionType.PICKUP, unit.id, adjacent)

        # if closest_depot is not None:
        #     for adj in self.get_adjacent_positions(closest_depot):
        #         if adj in self.in_range:
        #             return UnitAction(UnitActionType.MOVE, unit.id, adj)

        closest_miner_position = self.get_closest_friendly_miner(unit.position)

        has_miner = closest_miner_position is not None
        has_depot = closest_depot is not None

        if has_depot and not has_miner:
            return UnitAction(UnitActionType.MOVE, unit.id, closest_depot)
        elif has_miner and not has_depot:
            # ps = self.get_closest_position(unit.position, self.get_adjacent_positions(closest_miner_position))
            return UnitAction(UnitActionType.MOVE, unit.id, closest_miner_position)
        elif has_miner and has_depot:
            if self.get_manhattan_distance(closest_depot, closest_miner_position) > 10:
                ps = self.get_closest_position(unit.position, self.get_adjacent_positions(closest_miner_position) + [closest_depot])
                return UnitAction(UnitActionType.MOVE, unit.id, ps)
            else:
                return UnitAction(UnitActionType.MOVE, unit.id, closest_depot)

        return UnitAction(UnitActionType.MOVE, unit.id, unit.position)

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
        carts = self.get_units_by_type(UnitType.CART)
        for cart in carts:
            if (cart != unit and
                cart.position in self.get_adjacent_positions(unit.position) and
                self.get_manhattan_distance(cart.position, self.my_crew.homeBase) < self.get_manhattan_distance(unit.position, self.my_crew.homeBase) and
                cart.blitzium == 0):
                    return UnitAction(UnitActionType.DROP, unit.id, cart.position)

        if self.my_crew.homeBase in self.get_adjacent_positions(unit.position):
            return UnitAction(UnitActionType.DROP, unit.id, self.my_crew.homeBase)

        adjs = []
        for adj in self.get_adjacent_positions(self.my_crew.homeBase):
            if adj in self.in_range and adj not in [u.position for u in self.units]:
                adjs += [adj]

        target = self.get_closest_position(unit.position, adjs)
        return UnitAction(UnitActionType.MOVE, unit.id, target) if target is not None else self.get_random_position(self.game_map.get_map_size())


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
        have_more_time = self.my_crew.prices.MINER * 3 < (self.total_ticks - self.current_tick)

        n_minables = len(self.get_minable_squares())
        n_dispatched = sum([1 for unit in self.get_units_by_type(UnitType.MINER) if unit.path])
        has_more_spots = n_minables > n_dispatched
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
        carts_to_clear_sources = 1 if total_drops >= 50 else 0
        # carts_to_clear_sources = sum([self.per_tick_value(source.position, source.blitzium/2) for source in self.game_map.depots if not self.is_in_enemy_zone(source.position)])
        carts_to_clear_miners = sum([self.per_tick_value(source.position, 25) for source in self.get_units_by_type(UnitType.MINER) if not self.is_in_enemy_zone(source.position)])
        targetCarts = carts_to_clear_miners + carts_to_clear_sources

        has_enough_carts = targetCarts < len(self.get_units_by_type(UnitType.CART))

        return has_cash and have_more_time and (not has_enough_carts) #and (not maxed_out)

    def should_buy_outlaw(self):
        if self.outlaws_available > 0:
            if len(self.crews) == 2:
                if self.blitzium >= 125 + self.my_crew.prices.OUTLAW:
                    return True
            else:
                if self.blitzium >= self.my_crew.prices.OUTLAW and self.has_challenger():
                    return True
        return False

    def has_challenger(self):
        for crew in self.crews:
            for unit in crew.units:
                if unit.type == UnitType.OUTLAW and not crew.id == self.my_id:
                    return True
        return False

    def flood_fill(self):
        map_matrix = np.asarray(self.game_map.tiles)
        map_matrix = np.where(map_matrix =='WALL',  255, map_matrix)
        map_matrix = np.where(map_matrix == 'MINE', 255, map_matrix)
        map_matrix = np.where(map_matrix == 'EMPTY', 0, map_matrix)
        map_matrix = np.where(map_matrix == 'BASE', 0, map_matrix)
        map_matrix_int = map_matrix.astype(int)
        for crew in self.crews:
            for unit in crew.units:
                if not unit.path and unit.position != self.my_crew.homeBase:
                    map_matrix_int[unit.position.x, unit.position.y] = 255
            if crew.id == self.my_id:
                continue
            else:
                map_matrix_int[crew.homeBase.x, crew.homeBase.y] = 255
                limitx1 = max(0, crew.homeBase.x-3)
                limitx2 = min(self.game_map.get_map_size()-1, crew.homeBase.x+3)
                limity1 = max(0, crew.homeBase.y-3)
                limity2 = min(self.game_map.get_map_size()-1, crew.homeBase.y + 3)
                for x in range(limitx1, limitx2+1, 1):
                    for y in range(limity1, limity2+1, 1):
                        map_matrix_int[x, y] = 255
        return map_matrix_int

    def get_in_range(self, my_crew, crews, game_map):
        in_range = []
        matrix_np = self.flood_fill().astype(np.uint8)
        mask = np.zeros(np.asarray(matrix_np.shape)+2, dtype=np.uint8)
        matrix_np[my_crew.homeBase.x, my_crew.homeBase.y] = 0
        start_pt = (my_crew.homeBase.y, my_crew.homeBase.x)
        cv2.floodFill(matrix_np, mask, start_pt, 255)
        mask = mask[1:-1, 1:-1]

        for x in range(0, mask.shape[0]):
            for y in range(0, mask.shape[1]):
                if mask[x,y] == 1:
                    in_range.append(Position(x, y))


        # explored = [my_crew.homeBase] + self.get_adjacent_positions(my_crew.homeBase)
        # unexplored = self.get_adjacent_positions(my_crew.homeBase)
        # in_range2 = [my_crew.homeBase]
        #
        # unit_pos = []
        # for crew in crews:
        #     for unit in crew.units:
        #         if not unit.path:
        #             unit_pos += [unit.position]
        #
        # while unexplored:
        #     exploring, unexplored = unexplored[0], unexplored[1:]
        #
        #     try:
        #         if game_map.get_tile_type_at(exploring) == TileType.EMPTY:
        #             if exploring not in unit_pos and not self.is_in_enemy_zone(exploring):
        #                 in_range2 += [exploring]
        #                 for next in self.get_adjacent_positions(exploring):
        #                     if next not in explored:
        #                         explored += [next]
        #                         unexplored += [next]
        #     except:
        #         continue
        return in_range