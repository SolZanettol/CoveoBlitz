from typing import List
from game_message import GameMessage, Position, Crew
from game_command import Action, UnitAction, UnitActionType
import random


class Bot:

    def get_next_move(self, game_message: GameMessage) -> List[Action]:
        """
        Here is where the magic happens, for now the moves are random. I bet you can do better ;)

        No path finding is required, you can simply send a destination per unit and the game will move your unit towards
        it in the next turns.
        """
        my_crew: Crew = game_message.get_crews_by_id()[game_message.crewId]

        actions: List[UnitAction] = [UnitAction(UnitActionType.MOVE,
                                                unit.id,
                                                self.get_random_position(
                                                    game_message.map.get_map_size())) for unit in my_crew.units]

        return actions

    def get_random_position(self, map_size: int) -> Position:
        return Position(random.randint(0, map_size - 1), random.randint(0, map_size - 1))
