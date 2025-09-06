import pygame as p
import numpy as np
import pandas as pd
from board import Board
from flipper_chess import draw_game_state, load_images

LIGHT, DARK = p.Color("#FCC07F"), p.Color("#B76328")
ROW_HEIGHT = 1 / 3
HEIGHT = 800 # in pixels
WIDTH = int(HEIGHT * 1.5)
DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
MAX_FPS = 15
IMAGES = {} # for the pieces
TAPE_DF = None
BOARD_LIST = []
OTHER_SIDE = {"W": "B", "B": "W"}


def load_board_list(filename):
    global BOARD_LIST, TAPE_DF
    board = Board(None, None)
    TAPE_DF = pd.read_csv(filename)
    TAPE_DF["past"] = (TAPE_DF["success"] == "S").cumsum().shift(1).fillna(0)
    moves = TAPE_DF[TAPE_DF["success"] == "S"]
    BOARD_LIST = [board.copy()]
    for move in moves["move"]:
        board.process_move(move)
        BOARD_LIST.append(board.copy())


def main():
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    running = True

    load_images()
    filename = "tapes/2025-09-02 19-02-27.csv"
    load_board_list(filename)
    index = 0
    side = "W"

    while running:
        shortened_tape = TAPE_DF[TAPE_DF["past"] < index]
        tape = shortened_tape.drop("past", axis=1).values.tolist()
        draw_game_state(
            screen, BOARD_LIST[index], tape, colour=side, th=8
        )
        waiting = True
        while waiting:
            for e in p.event.get():
                if e.type == p.KEYDOWN:
                    waiting = False
                    if e.key == p.K_q: # i.e., quit
                        return
                    elif e.key in [p.K_SPACE, p.K_RIGHT]: # i.e., next move
                        index = min([len(BOARD_LIST) - 1, index + 1])
                    elif e.key == p.K_LEFT: # i.e., back one move
                        index = max([0, index - 1])
                    elif e.key == p.K_UP: # i.e., back to start
                        index = 0
                    elif e.key == p.K_DOWN: # i.e., to end
                        index = len(BOARD_LIST) - 1
                    elif e.key == p.K_s: # i.e., swap sides
                        side = OTHER_SIDE[side]
                    else:
                        waiting = True


if __name__ == "__main__":
    main()
