import pandas as pd
import numpy as np
import random
import torch
import time

from board import Board
from players import BozoBot, AutoDeep, OneLayer, FlatBot
from runner import do_move, run_game


def run_with_counter(white, black, counter):
    """ helper function, really only adds the counter functionality """
    print(f"\rRunning game {counter + 1}... {'-\\|/'[counter % 4]}", end="")
    outcome = run_game(white, black)
    return outcome[1]

def run_head_to_head(black, white, black_name, white_name, num_iterations):
    """ for given (white, black) play n games, print out results """
    results = pd.Series([
        run_with_counter(white, black, i)
        for i in range(num_iterations)
    ]).value_counts()
    def get_from_results(index):
        return results.loc[index] if index in results.index else 0
    print("\n_________")
    print(f"{white_name} wins as white: {get_from_results(1)}")
    print(f"{black_name} wins as black: {get_from_results(-1)}")
    print(f"Draws: {get_from_results(0)}")
    print("_________\n")


num_iterations = 1000
white = FlatBot("W", "../models/big_flat_4.pt")
white_name = "BigFlat 4.0"
black = BozoBot("B")#, "../models/big_flat_3.pt")
black_name = "BozoBot"
# black = AutoDeep("B", "../models/second_pass.pt")
# black_name = "AutoDeep 2.0"

start = time.time()
run_head_to_head(black, white, black_name, white_name, num_iterations)
white, black = black, white
white_name, black_name = black_name, white_name
white.colour, black.colour = "W", "B" # VERY important step
run_head_to_head(black, white, black_name, white_name, num_iterations)
print(f"Time elapsed: {time.time() - start:.2f}s")
