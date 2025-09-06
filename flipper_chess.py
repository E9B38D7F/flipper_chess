import pygame as p
import numpy as np
import pandas as pd
import time
from board import Board
from players import BozoBot, HumanPlayer, CppBot
from evals import (
    generate_complex_eval_dict,
    get_board_score_with_position,
    get_board_score_with_mobility
)

SUCCESS_PROB = 0.5 # VARIANT: randomly chosen at start of game
HEIGHT = 800 # in pixels
WIDTH = int(HEIGHT * 1.5)
DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
MAX_FPS = 15
IMAGES = {} # for the pieces
OTHER_PLAYER = {"B": "W", "W": "B"}
FILE_TO_COL = dict(zip("ABCDEFGH", range(8)))
COL_TO_FILE = dict(zip(range(8), "ABCDEFGH"))
LIGHT, DARK = p.Color("#FCC07F"), p.Color("#B76328")
ROW_HEIGHT = 1 / 3
TAPE = [] # list of tuples: (colour, succeed/fail, proposed_move)
def atb(row, col): return COL_TO_FILE[col] + str(row + 1) # array-to-board
def bta(tile): return (int(tile[1]) - 1, FILE_TO_COL[tile[0]]) # board-to-array


def load_images():
    global IMAGES
    IMAGES = {
        f"{piece}{colour}": p.transform.scale(
            p.image.load(f"svgs/{piece}{colour}.svg"),
            (SQ_SIZE, SQ_SIZE)
        )
        for piece in "PNBRQK"
        for colour in "WB"
    }


def get_rect(top_edge, bottom_edge, left_edge, right_edge):
    """ NOTE: this is in terms of squares, NOT pixels """
    return p.Rect(
        left_edge * SQ_SIZE,
        top_edge * SQ_SIZE,
        (right_edge - left_edge) * SQ_SIZE,
        (bottom_edge - top_edge) * SQ_SIZE
    )


def draw_text(screen, text, colour, size=28, cen=(4, 4)):
    """ Puts some text on top of the screen; centre is in square numbers """
    font = p.font.SysFont("menlo", size * HEIGHT // 512, True, False)
    rendered_text = font.render(text, 0, p.Color(colour))
    text_location = p.Rect(0, 0, HEIGHT, HEIGHT).move( # move to the middle
        HEIGHT / 2 - rendered_text.get_width() / 2 + (cen[0] - 4) * SQ_SIZE,
        HEIGHT / 2 - rendered_text.get_height() / 2 + (cen[1] - 4) * SQ_SIZE,
    )
    screen.blit(rendered_text, text_location)
    p.display.flip()


def get_highlights(board, square, colour, poss_moves):
    """ Returns a list of squares, in board format that piece can move to """
    piece = board.tiles[bta(square)]
    if len(piece) == 0 or piece[-1:] != colour: # i.e., not your piece
        return []
    target_tiles = [ # This handles en passant and promotion automatically
        move.split("=")[0][-2:] for move in poss_moves
        if move[0:3] == piece[0] + square
    ]
    if piece[0] == "K": # Handle castling separately
        back_rank = "1" if colour == "W" else "8"
        if "O-O" in poss_moves:
            target_tiles.append(f"G{back_rank}")
        if "O-O-O" in poss_moves:
            target_tiles.append(f"C{back_rank}")
    return target_tiles


def turn_clicks_to_move(player_clicks, board, poss_moves, screen):

    def display_promotion_options(ssq, esq, pm, pc, screen):
        margin = 0.1
        p.draw.rect( # Draw rectangle in middle of screen
            screen,
            p.Color("#000000"),
            get_rect(3.5 - margin, 4.5 + margin, 2 - margin, 6 + margin)
        )
        prom_pieces = [ # Get possible promotion moves
            move[-1] for move in pm
            if move[0] == "P" and move[1:3] == ssq
            and "=" in move and move.split("=")[0][-2:] == esq
        ]
        for index, piece in zip(range(4), "QRNB"):
            p.draw.rect( # Do the shading for if it's a legal move
                screen,
                p.Color("#BCBAFF" if piece in prom_pieces else "#000000"),
                get_rect(3.5, 4.5, 2 + index, 3 + index)
            )
            screen.blit( # Put the piece in there
                IMAGES[f"{piece}{pc}"],
                get_rect(3.5, 4.5, 2 + index, 3 + index)
            )
        p.display.flip()

    def get_promotion_piece():
        # Just wait for them to click
        # Check if location of click is in the right box
        # If it's not, return empty string (ie illegal move, resets inputter)
        while True:
            for e in p.event.get():
                if e.type == p.MOUSEBUTTONDOWN:
                    location = p.mouse.get_pos()
                    if abs(location[1] - HEIGHT / 2) > SQ_SIZE // 2: # row bad
                        return ""
                    box_num = int((location[0] - 2 * SQ_SIZE) // SQ_SIZE)
                    if box_num in [0, 1, 2, 3]:
                        print(box_num)
                        return "QRNB"[box_num]
                    else: # col bad
                        return ""

    starting_square = atb(
        player_clicks[0][0], player_clicks[0][1]
    )
    starting_piece = board.tiles[bta(starting_square)]
    ending_square = atb(
        player_clicks[1][0], player_clicks[1][1]
    )
    ending_piece = board.tiles[
        player_clicks[1][0], player_clicks[1][1]
    ]
    waiting = False
    if len(starting_piece) == 0:
        return ""
    # 0. NORMAL CASE
    proposed_move = (
        starting_piece[:1]
        + starting_square
        + ("" if len(ending_piece) == 0 else "x")
        + ending_square
    )
    # 1. Special case: en passant
    if (
        starting_piece[0] == "P"
        and ending_piece == ""
        and "x" not in proposed_move
        and starting_square[0] != ending_square[0]
    ):
        proposed_move = proposed_move[:3] + "x" + proposed_move[3:]
    # 2. Special case: castling
    back_rank = "1" if board.current_player == "W" else "8"
    if (
        starting_piece[0] == "K"
        and starting_square == "E" + back_rank
    ): # no cleaning here, Board object checks if castling is possible
        if ending_square == "G" + back_rank:
            proposed_move = "O-O"
        elif ending_square == "C" + back_rank:
            proposed_move = "O-O-O"
    # 3. Special case: promotion
    last_rank = "8" if board.current_player == "W" else "1"
    print(starting_piece, ending_square, last_rank)
    if (starting_piece[0] == "P" and ending_square[-1] == last_rank):
        # Make a pop-up which shows the four possible pieces
            # Highlighted if that is the right move
        display_promotion_options(
            starting_square,
            ending_square,
            poss_moves,
            board.current_player,
            screen
        )
        # Then make it register clicks:
            # If on a legal one, take down that move
            # If on an illegal one or outside the box, send "", illegal move
        piece = get_promotion_piece()
        proposed_move += f"={piece}"
    print(starting_piece[0] == "P", ending_square[-1] == last_rank)
    print(f"Proposed move is: {proposed_move}")
    return proposed_move


def draw_game_state(screen, board, tape, highlights=[], colour="W", th=6):
    """ th is tape_height """
    def draw_squares(screen, colour):
        # The background, i.e., the checkerboard
        colours = [LIGHT, DARK]
        for row in range(DIMENSION):
            for col in range(DIMENSION):
                colour = colours[(row + col) % 2] # 0 for light, 1 for dark
                c = col if colour == "W" else 7 - col
                r = row if colour == "W" else 7 - row
                p.draw.rect(screen, colour, get_rect(r, r + 1, c, c + 1))
    def draw_highlights(screen, highlights, colour):
        for highlight in highlights:
            board_form = bta(highlight)
            row, col = 7 - board_form[0], board_form[1]
            c = col if colour == "W" else 7 - col
            r = row if colour == "W" else 7 - row
            p.draw.rect(
                screen, p.Color("#BCBAFF"),
                get_rect(r, r + 1, c, c + 1)
            )
    def draw_pieces(screen, board, colour):
        for row in range(DIMENSION):
            for col in range(DIMENSION):
                current_piece = board.tiles[7 - row][col]
                c = col if colour == "W" else 7 - col
                r = row if colour == "W" else 7 - row
                if len(current_piece) > 0:
                    screen.blit(
                        IMAGES[current_piece],
                        get_rect(r, r + 1, c, c + 1)
                    )
    def draw_sidebar(screen, tape):
        def write_tape_row(index, row):
            ac = 9 if row["colour"] == "W" else 11
            dn = ROW_HEIGHT * (index + 1 / 2)
            colour = "Green" if row["success"] == "S" else "Red"
            draw_text(screen, row["move"], colour, size=18, cen=(ac, dn))
        p.draw.rect(screen, p.Color("#6E3E02"), get_rect(0, 8, 8, 12))
        tape_df = pd.DataFrame(tape, columns=["colour", "success", "move"])
        printable = tape_df.tail(int(th / ROW_HEIGHT))
        for index, row in printable.reset_index().iterrows():
            write_tape_row(index, row)
        if th > 6: # i.e., no space for buttons
            return
        p.draw.rect(screen, LIGHT, get_rect(6.1, 6.9, 8.1, 11.9))
        p.draw.rect(screen, DARK, get_rect(6.2, 6.8, 8.2, 11.8))
        p.draw.rect(screen, LIGHT, get_rect(7.1, 7.9, 8.1, 11.9))
        p.draw.rect(screen, DARK, get_rect(7.2, 7.8, 8.2, 11.8))
        draw_text(screen, "Save and quit", LIGHT, size=16, cen=(10, 6.5))
        draw_text(screen, "Quit without saving", LIGHT, size=16, cen=(10, 7.5))
    draw_squares(screen, colour)
    draw_highlights(screen, highlights, colour)
    draw_pieces(screen, board, colour)
    draw_sidebar(screen, tape)
    p.display.flip()


def choose_players(screen):
    def select_player(screen, colour):
        # Draw relevant things
        screen.fill(LIGHT)
        draw_text(
            screen, f"Choose {colour} player type", DARK, size=32, cen=(6, 2)
        )
        p.draw.rect(screen, DARK, get_rect(3.5, 4.5, 3, 9))
        p.draw.rect(screen, DARK, get_rect(5, 6, 3, 9))
        draw_text(screen, "Human", LIGHT, cen=(6, 4))
        draw_text(screen, "Computer", LIGHT, cen=(6, 5.5))
        time.sleep(0.1)
        p.display.flip()
        # Now get player input
        while True:
            for e in p.event.get():
                if e.type == p.MOUSEBUTTONDOWN:
                    location = p.mouse.get_pos()
                    if abs(location[0] - 6 * SQ_SIZE) < 3 * SQ_SIZE:
                        if abs(location[1] - 4 * SQ_SIZE) < SQ_SIZE / 2:
                            return HumanPlayer(colour[0])
                        elif abs(location[1] - 5.5 * SQ_SIZE) < SQ_SIZE / 2:
                            # return BozoBot(colour[0])
                            return CppBot(colour[0], 1000, 4000000)
    def select_time(screen):
        tt = 10
        while True:
            # Draw all the things
            screen.fill(LIGHT)
            draw_text(
                screen, f"Thinking time: {tt}", DARK, size=32, cen=(6, 2)
            )
            p.draw.rect(screen, DARK, get_rect(3.5, 4.5, 3, 5.5))
            p.draw.rect(screen, DARK, get_rect(3.5, 4.5, 6.5, 9))
            p.draw.rect(screen, DARK, get_rect(5, 6, 3, 9))
            draw_text(screen, "Halve", LIGHT, cen=(4.25, 4))
            draw_text(screen, "Double", LIGHT, cen=(7.75, 4))
            draw_text(screen, "Submit", LIGHT, cen=(6, 5.5))
            time.sleep(0.1)
            p.display.flip()
            # Now let's see what the user thinks
            in_loop = True
            while in_loop:
                for e in p.event.get():
                    if e.type == p.MOUSEBUTTONDOWN:
                        l = [i / SQ_SIZE for i in p.mouse.get_pos()]
                        if abs(l[0] - 6) < 0.5 and abs(l[1] - 5.5) < 3:
                            return tt
                        elif abs(l[0] - 4.25) < 0.5 and abs(l[1] - 4) < 1.25:
                            tt /= 2
                            in_loop = False
                            break
                        elif abs(l[0] - 7.75) < 0.5 and abs(l[1] - 4) < 1.25:
                            tt *= 2
                            in_loop = False
                            break
    return select_player(screen, "WHITE"), select_player(screen, "BLACK")


def handle_ending(screen, board):
    def draw_ending_screen(screen, board):
        draw_game_state(screen, board, TAPE)
        for marg, colour in zip([0.1, 0], [DARK, LIGHT]):
            p.draw.rect(
                screen, colour,
                get_rect(1.5 - marg, 6.5 + marg, 0.5 - marg, 7.5 + marg)
            )
        # Draw in the buttons
        for top in [3.5, 5]:
            p.draw.rect(
                screen, DARK,
                get_rect(top, top + 1, 1, 7)
            )
        for message, colour, size, row in zip(
            ["GAME OVER", "Save and quit", "Quit without saving"],
            [DARK, LIGHT, LIGHT], [36, 28, 28], [2.5, 4, 5.5]
        ):
            draw_text(screen, message, colour, size=size, cen=(4, row))
        p.display.flip()
    def get_ending_click(screen, board):
        while True:
            for e in p.event.get():
                if e.type == p.MOUSEBUTTONDOWN:
                    location = p.mouse.get_pos()
                    if abs(location[0] - 4 * SQ_SIZE) < 3 * SQ_SIZE: # row
                        if abs(location[1] - 4 * SQ_SIZE) < SQ_SIZE / 2:
                            print("SAVING TO FILE")
                            save_tape_to_file()
                            return
                        elif abs(location[1] - 5.5 * SQ_SIZE) < SQ_SIZE / 2:
                            print("QUITTING")
                            return
    draw_ending_screen(screen, board)
    get_ending_click(screen, board)


def save_tape_to_file():
    filename = f"tapes/{time.strftime('%Y-%m-%d %H-%M-%S')}.csv"
    tape_df = pd.DataFrame(TAPE, columns=["colour", "success", "move"])
    tape_df.to_csv(filename, index=False)


def load_position(board, data_list):
    deencoder = {
        6: "KW", 5: "QW", 4: "RW", 3: "BW", 2: "NW", 1: "PW",
        -6: "KB", -5: "QB", -4: "RB", -3: "BB", -2: "NB", -1: "PB",
        0: ""
    }
    tiles = np.vectorize(deencoder.__getitem__)(np.array(data_list[:64]))
    board.tiles = tiles.reshape(8, 8)
    board.castle_list = []
    for i, poss in zip(range(64, 68), ["WK", "WQ", "BK", "BQ"]):
        if data_list[i] == 1:
            board.castle_list.append(poss)
    if data_list[68] == -1:
        board.epsq = "none"
    else:
        board.epsq = "ABCDEFGH"[data_list[68] % 8] + str(data_list[68] // 8)
    board.current_player = "W" if data_list[69] == 0 else "B"


def main():
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()

    white, black = choose_players(screen)
    board = Board(white, black)
    load_images()
    running = True
    sel_square = ()
    player_clicks = []
    draw_game_state(screen, board, TAPE)

    while running: # ONE loop of this loop is getting a move
        new_board = True
        current_player = board.players[board.current_player]
        poss_moves = board.get_all_possible_moves(board.current_player)
        imp_moves = []
        while True: # One loop of this = one requested move from the player
            # 1. Collect the proposed move
            if type(current_player) == HumanPlayer: # So take human input
                waiting = True
                draw_game_state(
                    screen, board, TAPE, colour=current_player.colour
                )
                while waiting:
                    for e in p.event.get():
                        if e.type == p.QUIT:
                            running=False
                        elif e.type == p.MOUSEBUTTONDOWN:
                            location = p.mouse.get_pos()
                            col = location[0] // SQ_SIZE
                            row = 7 - (location[1] // SQ_SIZE)
                            if col > 7 and row == 1:
                                save_tape_to_file()
                                draw_text(screen, "Saved!", "Green", size=36)
                                time.sleep(0.25)
                                return
                            elif col > 7 and row == 0:
                                draw_text(screen, "Quitting", "Green", size=36)
                                time.sleep(0.25)
                                return
                            if current_player.colour == "B":
                                col = 7 - col
                                row = 7 - row
                            if sel_square == (row, col): # i.e., old square
                                sel_square = ()
                                player_clicks = []
                            else:
                                sel_square = (row, col)
                                player_clicks.append(sel_square)
                            if len(player_clicks) == 2: # time to move!
                                waiting = False
                                break
                            elif len(player_clicks) == 1: # highlight poss
                                highlights = get_highlights(
                                    board, atb(sel_square[0], sel_square[1]),
                                    current_player.colour, poss_moves
                                )
                                draw_game_state(
                                    screen, board, TAPE, highlights=highlights,
                                    colour=current_player.colour
                                )
                proposed_move = turn_clicks_to_move(
                    player_clicks, board, poss_moves, screen
                )
                sel_square = ()
                player_clicks = []
            else: # If automated player
                board.send_info_to_player(
                    current_player, poss_moves, imp_moves, new_board=new_board
                )
                new_board = False
                proposed_move = board.get_move_from_player(current_player)
            # 2. Check it is possible
            if proposed_move not in poss_moves:
                print("Not a possible move!")
                continue
            # 3. Flip the coin
            move_succeeds = np.random.uniform(0, 1) < SUCCESS_PROB
            if move_succeeds:
                print(f"Flip succeeds! {proposed_move} accepted")
                TAPE.append((board.current_player, "S", proposed_move))
                draw_game_state(screen, board, TAPE)
                draw_text(
                    screen, f"Flip succeeds! {proposed_move} accepted", "Green"
                )
                time.sleep(1)
                break
            else:
                print(f"Flip fails! {proposed_move} rejected")
                TAPE.append((board.current_player, "F", proposed_move))
                poss_moves.remove(proposed_move)
                imp_moves.append(proposed_move)
                draw_game_state(
                    screen, board, TAPE, colour=board.current_player
                )
                draw_text(
                    screen, f"Flip fails! {proposed_move} rejected", "Red"
                )
                time.sleep(1)
                if len(poss_moves) == 0:
                    print(f"{current_player} has no moves and loses")
                    board.outcome = OTHER_PLAYER[board.current_player] + "wins"
                    running = False
                    time.sleep(1)
                    break
                continue
        # 4. Process the move
        board.process_move(proposed_move)
        if f"K{board.current_player}" not in board.tiles.flatten():
            print(f"King taken! {board.current_player} loses!")
            board.outcome = OTHER_PLAYER[board.current_player] + " wins"
            running = False
        draw_game_state(screen, board, TAPE)
        clock.tick(MAX_FPS)
    # Show ending screen
    time.sleep(1)
    handle_ending(screen, board)


if __name__ == "__main__":
    main()
