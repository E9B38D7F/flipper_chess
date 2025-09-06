import pandas as pd
import numpy as np
import random
import torch

from board import Board
from players import BozoBot, AutoDeep, OneLayer, FlatBot


SUCCESS_PROB = 0.5


def do_move(board, tape):
    """
    Returns (board, tape, game_outcome)
    game_outcome is +50 if white wins, -50 if black wins, 0 if game ongoing
    """
    current_player = board.players[board.current_player]
    poss_moves = board.get_all_possible_moves(board.current_player)
    imp_moves = []
    new_board = True
    while True:
        if len(poss_moves) == 0:
            game_outcome = 50 if board.current_player == "W" else -50
            return board, tape, game_outcome
        board.send_info_to_player(
            current_player,
            poss_moves,
            imp_moves,
            new_board=new_board
        )
        proposed_move = board.get_move_from_player(current_player)
        move_fails = np.random.uniform(0, 1) > SUCCESS_PROB
        if move_fails:
            new_board = False
            tape.append((board.current_player, "F", proposed_move))
            poss_moves.remove(proposed_move)
            imp_moves.append(proposed_move)
            continue
        tape.append((board.current_player, "S", proposed_move))
        break
    board.process_move(proposed_move)
    if f"K{board.current_player}" not in board.tiles.flatten():
        game_outcome = -50 if board.current_player == "W" else 50
        return board, tape, game_outcome
    return board, tape, 0

def run_game(white, black, max_moves=500):
    """
    Simple: run a game and save all board states into dataframe
    Returns that dataframe and a signed bit for the game result
    """
    board = Board(white, black)
    tape = []
    game_outcome = 0
    game_states = []
    while ((game_outcome == 0) and (len(tape) < max_moves // 2)):
        board, tape, game_outcome = do_move(board, tape)
        game_states.append(board.export())
    columns = (
        [f"sq_{i}" for i in range(64)]
        + ["O-Ow", "O-O-Ow", "O-Ob", "O-O-Ob"]
        + ["epsq"]
        + ["mover"]
    )
    game_df = pd.DataFrame(game_states, columns=columns)
    return game_df, game_outcome // 50

def run_whole_process(white, black, id, max_moves=500):
    """
    Not the WHOLE process, just one iteration of the process
    runs a game, saves board state after each half-move in export format
    adds bonus columns: signed bit for game result
    and one for the game id, so final df has each game be identifiable
    """
    game_df, game_outcome = run_game(white, black, max_moves=max_moves)
    game_df["outcome"] = game_outcome
    game_df["game_id"] = id
    return game_df


if __name__ == "__main__":
    iterations = 1000
    name = "5_1k_bigflat3"
    white = BozoBot("W")
    black = BozoBot("B")
    processed_dfs = []
    for i in range(iterations):
        processed_df = run_whole_process(white, black, i, max_moves=256)
        processed_dfs.append(processed_df)
        print(f"\rProcessed {i + 1}", end="")
    print("\n")
    pd.concat(processed_dfs).to_csv(f"../data/{name}.csv", index=False)
