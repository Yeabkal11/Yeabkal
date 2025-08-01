from typing import Dict, Any
from bot.game_logic import LudoGame

def render_board(game_state: Dict[str, Any]) -> str:
    """Generates an emoji-based representation of the Ludo board."""
    PLAYER_ICONS = {'RED': '🔴', 'GREEN': '🟢', 'YELLOW': '🟡', 'BLUE': '🔵'}
    PATH_ICON = '⬜'
    SAFE_ICON = '⭐'
    
    board = [PATH_ICON] * LudoGame.BOARD_SIZE
    for pos in LudoGame.SAFE_ZONES:
        board[pos] = SAFE_ICON

    player_positions = {}
    for pid, pdata in game_state['players'].items():
        color = pdata['color']
        icon = PLAYER_ICONS[color]
        for pos in pdata['tokens']:
            if 0 <= pos < LudoGame.BOARD_SIZE:
                if pos in player_positions:
                    player_positions[pos].append(icon)
                else:
                    player_positions[pos] = [icon]

    for pos, icons in player_positions.items():
        if len(icons) > 1:
            board[pos] = f"{len(icons)}{icons[0]}"
        else:
            board[pos] = icons[0]
            
    # Simple linear representation for robustness in Telegram
    board_str = ' '.join(board)
    
    info_lines = []
    for pid in game_state['player_order']:
        pdata = game_state['players'][pid]
        icon = PLAYER_ICONS[pdata['color']]
        tokens_home = sum(1 for t in pdata['tokens'] if t == 107)
        tokens_yard = sum(1 for t in pdata['tokens'] if t == -1)
        info_lines.append(f"{icon} {pdata['username']}: 🏆x{tokens_home}, 🏠x{tokens_yard}")

    info_str = "\n".join(info_lines)
    
    current_player_id = game_state['player_order'][game_state['turn_index']]
    current_player_data = game_state['players'][current_player_id]
    current_player_icon = PLAYER_ICONS[current_player_data['color']]
    
    status_text = ""
    if game_state['status'] == 'active':
        if game_state.get('dice_roll'):
            status_text = f"🎲 {current_player_icon} rolled a {game_state['dice_roll']}! Choose a token."
        else:
            status_text = f"Turn: {current_player_icon} {current_player_data['username']}. Roll the dice!"
    elif game_state['status'] == 'finished':
        winner_id = [pid for pid, pdata in game_state['players'].items() if sum(1 for t in pdata['tokens'] if t == 107) >= game_state['win_condition']][0]
        winner_data = game_state['players'][winner_id]
        status_text = f"🎉 Game Over! {PLAYER_ICONS[winner_data['color']]}{winner_data['username']} wins!"
    elif game_state['status'] == 'forfeited':
        winner_id = [pid for pid in game_state['player_order'] if str(pid) not in str(current_player_id)][0]
        winner_data = game_state['players'][winner_id]
        status_text = f"Game Forfeited. {PLAYER_ICONS[winner_data['color']]}{winner_data['username']} wins!"

    return f"{info_str}\n\n`{board_str}`\n\n{status_text}"