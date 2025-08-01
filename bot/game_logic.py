import random
from typing import Dict, List, Optional, Any

class LudoGame:
    """Manages the state and rules of a Ludo game."""

    BOARD_SIZE = 52
    HOME_PATH_SIZE = 6
    SAFE_ZONES = [0, 8, 13, 21, 26, 34, 39, 47]
    PLAYER_STARTS = {'RED': 0, 'GREEN': 13, 'YELLOW': 26, 'BLUE': 39}
    PLAYER_HOME_ENTRIES = {'RED': 50, 'GREEN': 11, 'YELLOW': 24, 'BLUE': 37}

    def __init__(self, state: Dict[str, Any]):
        self.state = state

    @classmethod
    def new_game(cls, player1_id: int, player1_username: str, stake: int, win_condition: int) -> 'LudoGame':
        """Initializes a brand new game waiting for a second player."""
        state = {
            "players": {
                player1_id: {
                    "username": player1_username,
                    "color": "RED",
                    "tokens": [-1, -1, -1, -1] # -1: yard, 0-51: board, 101-106: home path, 107: home
                }
            },
            "player_order": [player1_id],
            "turn_index": 0,
            "pot": stake,
            "stake_per_player": stake,
            "win_condition": win_condition, # 1, 2, or 4 tokens home
            "dice_roll": None,
            "roll_history": [],
            "game_id": None,
            "status": "lobby",
            "message_id": None,
            "chat_id": None,
        }
        return cls(state)

    def add_player(self, player2_id: int, player2_username: str):
        """Adds the second player and starts the game."""
        player2_color = "YELLOW"
        
        self.state['players'][player2_id] = {
            "username": player2_username,
            "color": player2_color,
            "tokens": [-1, -1, -1, -1]
        }
        self.state['player_order'].append(player2_id)
        random.shuffle(self.state['player_order']) # Randomize who goes first
        self.state['pot'] += self.state['stake_per_player']
        self.state['status'] = 'active'

    def current_player_id(self) -> int:
        return self.state['player_order'][self.state['turn_index']]

    def roll_dice(self) -> int:
        """Rolls the dice and handles turn logic for rolling 6."""
        roll = random.randint(1, 6)
        self.state['dice_roll'] = roll
        current_player_id = self.current_player_id()
        
        if roll == 6:
            self.state['roll_history'].append(6)
            if len(self.state['roll_history']) == 3:
                self.next_turn()
                return roll
        else:
            self.state['roll_history'] = []
        
        if not self.get_possible_moves(current_player_id, roll):
            self.next_turn()
        
        return roll

    def get_possible_moves(self, player_id: int, roll: int) -> List[int]:
        """Returns a list of token indices that can be moved."""
        possible_moves = []
        player = self.state['players'][player_id]
        
        for i, pos in enumerate(player['tokens']):
            if self.is_move_valid(player_id, i, roll):
                possible_moves.append(i)
        return possible_moves

    def is_move_valid(self, player_id: int, token_index: int, roll: int) -> bool:
        """Checks if a specific move is valid."""
        player = self.state['players'][player_id]
        token_pos = player['tokens'][token_index]

        if token_pos == 107: # Already home
            return False
        
        if token_pos == -1 and roll != 6: # In yard, need a 6
            return False
        
        if token_pos >= 101: # In home path
            return token_pos + roll <= 107 # Cannot overshoot home

        return True

    def move_token(self, player_id: int, token_index: int) -> Optional[Dict[str, Any]]:
        """Moves a token, handles knockouts, and checks for win condition."""
        roll = self.state['dice_roll']
        player = self.state['players'][player_id]
        color = player['color']
        token_pos = player['tokens'][token_index]

        # 1. Enter token from yard
        if token_pos == -1 and roll == 6:
            start_pos = self.PLAYER_STARTS[color]
            player['tokens'][token_index] = start_pos
            self.knockout_check(start_pos, player_id)
        
        # 2. Move within home path
        elif token_pos >= 101:
            player['tokens'][token_index] += roll
        
        # 3. Standard move on main board
        else:
            home_entry = self.PLAYER_HOME_ENTRIES[color]
            new_pos_abs = (self.PLAYER_STARTS[color] + token_pos) % self.BOARD_SIZE
            
            # Check for passing home entry
            if token_pos <= home_entry < (token_pos + roll):
                home_path_pos = 101 + (token_pos + roll - home_entry - 1)
                player['tokens'][token_index] = home_path_pos
            else:
                final_pos = (token_pos + roll) % self.BOARD_SIZE
                player['tokens'][token_index] = final_pos
                self.knockout_check(final_pos, player_id)

        self.state['dice_roll'] = None # Consume the roll
        
        winner = self.check_win_condition()
        if winner:
            self.state['status'] = 'finished'
            return {'winner': winner}
        
        if roll != 6:
            self.next_turn()

        return None

    def knockout_check(self, position: int, current_player_id: int):
        """Checks for and performs a knockout on a given board position."""
        if position in self.SAFE_ZONES:
            return

        occupants = []
        for pid, pdata in self.state['players'].items():
            for t_pos in pdata['tokens']:
                if t_pos == position:
                    occupants.append(pid)
        
        if len(occupants) > 1 and len(set(occupants)) == 1:
            return # It's a block, no knockout

        for other_player_id, other_player_data in self.state['players'].items():
            if other_player_id == current_player_id:
                continue
            for i, token_pos in enumerate(other_player_data['tokens']):
                if token_pos == position:
                    other_player_data['tokens'][i] = -1

    def check_win_condition(self) -> Optional[int]:
        """Checks if any player has met the win condition."""
        for player_id, player_data in self.state['players'].items():
            tokens_home = sum(1 for pos in player_data['tokens'] if pos == 107)
            if tokens_home >= self.state['win_condition']:
                return player_id
        return None

    def next_turn(self):
        """Advances the turn to the next player."""
        self.state['turn_index'] = (self.state['turn_index'] + 1) % len(self.state['player_order'])
        self.state['dice_roll'] = None
        self.state['roll_history'] = []

    def forfeit(self, player_id: int) -> int:
        """Forfeits the game for a player and returns the winner's ID."""
        self.state['status'] = 'forfeited'
        winner_id = [pid for pid in self.state['player_order'] if pid != player_id][0]
        return winner_id