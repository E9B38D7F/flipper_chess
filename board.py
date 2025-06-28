import numpy as np


# Various constants to import
pdict = {
    "KW": "\u2654", "QW": "\u2655", "RW": "\u2656",
    "BW": "\u2657", "NW": "\u2658", "PW": "\u2659",
    "KB": "\u265A", "QB": "\u265B", "RB": "\u265C",
    "BB": "\u265D", "NB": "\u265E", "PB": "\u265F",
    "": "."
} # i.e., piece_dict
file_to_col = dict(zip("ABCDEFGH", range(8)))
col_to_file = dict(zip(range(8), "ABCDEFGH"))
other_player = {"B": "W", "W": "B"}
def atb(row, col): return col_to_file[col] + str(row + 1) # array-to-board
def bta(tile): return (int(tile[1]) - 1, file_to_col[tile[0]]) # board-to-array



class Board():

    def __init__(self, white, black):
        self.tiles = np.array([
            [f"{piece}W" for piece in "RNBQKBNR"],
            ["PW"] * 8,
            [""] * 8,
            [""] * 8,
            [""] * 8,
            [""] * 8,
            ["PB"] * 8,
            [f"{piece}B" for piece in "RNBQKBNR"]
        ])
        self.last_move = "none"
        self.castle_list = ["WK", "WQ", "BK", "BQ"] # i.e., w/b king/queenside
        self.players = {"W": white, "B": black}
        self.current_player = "W" # i.e., key of whoever's move it is
        self.outcome = ""

    def copy(self):
        copy = Board(self.players["W"], self.players["B"])
        copy.tiles = self.tiles.copy()
        copy.last_move = "".join([i for i in self.last_move]) # i.e., copy str
        copy.castle_list = self.castle_list.copy()
        copy.current_player = other_player[self.current_player]
        return copy

    def display_tiles(self, colour="W"):
        """ primitive print method the board to terminal output """
        lines = []
        if colour == "W":
            for row, rank in zip(self.tiles[::-1], range(8, 0, -1)):
                lines.append(
                    f"{rank} | " + (" ").join([pdict[s] for s in row])
                )
            lines.append("    ---------------")
            lines.append("    A B C D E F G H")
        elif colour == "B":
            for row, rank in zip(self.tiles, range(1, 9)):
                lines.append(
                    f"{rank} | " + (" ").join([pdict[s] for s in row[::-1]])
                )
            lines.append("    ---------------")
            lines.append("    H G F E D C B A")
        block_text = "\n".join(lines)
        print(block_text)

    def get_all_possible_moves(self, colour):
        """
        Given colour, returns list of all possible moves, as strings
        Of form:
            NA6B4 if moving knight from A6 to B4
            BC1xB2 if bishop on C1 takes on B2
            PD7D8=Q if pawn on D7 promotes to queen by moving to D8
            O-O if kingside castle, O-O-O if queenside
        last_move is retained to check for en passant
        """
        def get_tile_moves(self, row, col, colour):
            """
            For given row, col, colour returns what moves the piece can do
            For pieces that can go along a line (e.g., bishop),
            it scans along that line until there's a point it can't go past
            """
            def get_king_moves(self, row, col, colour):
                poss_tiles = [
                    [row + i, col + j]
                    for i in [-1, 0, 1] for j in [-1, 0, 1]
                    if (row + i >= 0
                        and row + i <= 7
                        and col + j >= 0 and col + j <= 7
                    )
                ]
                poss_moves = []
                for tile in poss_tiles:
                    target_square = self.tiles[tile[0]][tile[1]]
                    if target_square == "":
                        poss_moves.append(
                            f"K{atb(row, col)}{atb(tile[0], tile[1])}"
                        )
                    elif (
                        len(target_square) == 2
                        and target_square[1] != colour
                    ):
                        poss_moves.append(
                            f"K{atb(row, col)}x{atb(tile[0], tile[1])}"
                        )
                return poss_moves

            def get_queen_moves(self, row, col, colour):
                return ["Q" + move[1:] for move in (
                    get_rook_moves(self, row, col, colour)
                    + get_bishop_moves(self, row, col, colour)
                )]

            def get_rook_moves(self, row, col, colour):
                poss_moves = []
                for dir in [[0, 1], [0, -1], [1, 0], [-1, 0]]:
                    new_row, new_col = row + dir[0], col + dir[1]
                    while (
                        new_row >= 0 and new_row <= 7
                        and new_col >= 0 and new_col <= 7
                    ):
                        tile_contents = self.tiles[new_row][new_col]
                        if len(tile_contents) == 2: # i.e., occupied square
                            if tile_contents[1] != colour:
                                poss_moves.append(
                                    f"R{atb(row, col)}x{atb(new_row, new_col)}"
                                )
                            break
                        poss_moves.append(
                            f"R{atb(row, col)}{atb(new_row, new_col)}"
                        )
                        new_row += dir[0]
                        new_col += dir[1]
                return poss_moves

            def get_bishop_moves(self, row, col, colour):
                poss_moves = []
                for dir in [[1, 1], [1, -1], [-1, 1], [-1, -1]]:
                    new_row, new_col = row + dir[0], col + dir[1]
                    while (
                        new_row >= 0 and new_row <= 7
                        and new_col >= 0 and new_col <= 7
                    ):
                        tile_contents = self.tiles[new_row][new_col]
                        if len(tile_contents) == 2:
                            if tile_contents[1] != colour:
                                poss_moves.append(
                                    f"B{atb(row, col)}x{atb(new_row, new_col)}"
                                )
                            break
                        poss_moves.append(
                            f"B{atb(row, col)}{atb(new_row, new_col)}"
                        )
                        new_row += dir[0]
                        new_col += dir[1]
                return poss_moves

            def get_knight_moves(self, row, col, colour):
                poss_moves = []
                for dir in [[1, 2], [2, 1], [-1, 2], [2, -1],
                            [1, -2], [-2, 1], [-1, -2], [-2, -1]]:
                    new_row, new_col = row + dir[0], col + dir[1]
                    if (
                        new_row < 0 or new_row > 7
                        or new_col < 0 or new_col > 7
                    ):
                        continue
                    tile_contents = self.tiles[new_row][new_col]
                    if len(tile_contents) == 0:
                        poss_moves.append(
                            f"N{atb(row, col)}{atb(new_row, new_col)}"
                        )
                    elif tile_contents[1] != colour:
                        poss_moves.append(
                            f"N{atb(row, col)}x{atb(new_row, new_col)}"
                        )
                return poss_moves

            def get_pawn_moves(self, row, col, colour):
                # NOTE: en passant handled separately
                poss_moves = []
                dir = 1 if colour == "W" else -1
                # a. Move one rank forward
                if self.tiles[row + dir][col] == "":
                    poss_moves.append(f"P{atb(row, col)}{atb(row + dir, col)}")
                # b. On original rank and move forward 2
                if (
                    (colour == "W" and row == 1)
                    or (colour == "B" and row == 6)
                ):
                    if (
                        self.tiles[row + dir][col] == ""
                        and self.tiles[row + 2 * dir][col] == ""
                    ):
                        poss_moves.append(
                            f"P{atb(row, col)}{atb(row + 2 * dir, col)}"
                        )
                # c. Take on diagonal
                for offset in [-1, 1]:
                    if col + offset < 0 or col + offset > 7:
                        continue
                    target_tile = self.tiles[row + dir][col + offset]
                    if len(target_tile) == 2:
                        if target_tile[-1] != colour:
                            poss_moves.append(
                                f"P{atb(row, col)}x{atb(row+dir, col+offset)}"
                            )
                # d. Promote
                if len(poss_moves) > 0 and poss_moves[0][-1] in ["1", "8"]:
                    new_poss_moves = []
                    for move in poss_moves:
                        new_poss_moves += [f"{move}={prom}" for prom in "QRBN"]
                    return new_poss_moves
                else:
                    return poss_moves

            if self.tiles[row][col][0] == "K":
                return get_king_moves(self, row, col, colour)
            elif self.tiles[row][col][0] == "Q":
                return get_queen_moves(self, row, col, colour)
            elif self.tiles[row][col][0] == "R":
                return get_rook_moves(self, row, col, colour)
            elif self.tiles[row][col][0] == "B":
                return get_bishop_moves(self, row, col, colour)
            elif self.tiles[row][col][0] == "N":
                return get_knight_moves(self, row, col, colour)
            elif self.tiles[row][col][0] == "P":
                return get_pawn_moves(self, row, col, colour)
            else:
                print("Something awful has happened")
                assert False

        if len(self.outcome) > 0: # i.e., game over
            return []
        poss_moves = []
        # 1. Castling
        back = 0 if colour == "W" else 7
        if (
            self.tiles[back,1] == ""
            and self.tiles[back,2] == ""
            and self.tiles[back,3] == ""
            and colour + "Q" in self.castle_list
        ):
            poss_moves.append("O-O-O")
        if (
            self.tiles[back,5] == ""
            and self.tiles[back,6] == ""
            and colour + "K" in self.castle_list
        ):
            poss_moves.append("O-O")
        # 2. En passant
        if "x" not in self.last_move:
            if (
                self.last_move[0] == "P"
                and abs(int(self.last_move[2]) - int(self.last_move[4])) == 2
            ):
                prow, pcol = bta(self.last_move[3:5])
                for offset in [-1, 1]:
                    if pcol + offset < 0 or pcol + offset > 7:
                        continue
                    if self.tiles[prow, pcol + offset] == "P" + colour:
                        end_row = 5 if colour == "W" else 2
                        poss_moves.append(
                            f"P{atb(prow, pcol + offset)}x{atb(end_row, pcol)}"
                        )
        # 3. Everything else
        for row in range(8):
            for col in range(8):
                tile = self.tiles[row][col]
                if len(tile) == 2:
                    if tile[-1] == colour:
                        poss_moves += get_tile_moves(self, row, col, colour)
        return poss_moves

    def update_castle_list(self):
        """ After move, check that castling hasn't been rules impossible """
        removals = []
        # Check king moves
        if self.tiles[0, 4] != "KW":
            removals += ["WK", "WQ"]
        if self.tiles[7, 4] != "KB":
            removals += ["BK", "BQ"]
        # Check rook moves
        if self.tiles[0][0] != "RW":
            removals.append("WQ")
        if self.tiles[0][7] != "RW":
            removals.append("WK")
        if self.tiles[7][0] != "RB":
            removals.append("BQ")
        if self.tiles[7][7] != "RB":
            removals.append("BK")
        for removal in set(removals) & set(self.castle_list):
            self.castle_list.remove(removal)


    def send_info_to_player(self, player, poss_moves, imp_moves):
        player.receive_info(self, poss_moves, imp_moves)

    def get_move_from_player(self, player):
        return player.send_move()

    def process_move(self, proposed_move, colour=None):
        if colour == None:
            colour = self.current_player
        # If castling
        if proposed_move == "O-O":
            rank = 0 if colour == "W" else 7
            self.tiles[rank][4] = ""
            self.tiles[rank][5] = "R" + colour
            self.tiles[rank][6] = "K" + colour
            self.tiles[rank][7] = ""
        elif proposed_move == "O-O-O":
            rank = 0 if colour == "W" else 7
            self.tiles[rank][0] = ""
            self.tiles[rank][1] = ""
            self.tiles[rank][2] = "K" + colour
            self.tiles[rank][3] = "R" + colour
            self.tiles[rank][4] = ""
        # If not
        else:
            leav_row, leav_col = bta(proposed_move[1:3])
            self.tiles[leav_row][leav_col] = ""
            targ_row, targ_col = bta(proposed_move.replace("x", "")[3:5])
            targ_tile = self.tiles[targ_row][targ_col]
            # Catch the rude and annoying case of en passant
            if "x" in proposed_move and targ_tile == "":
                taken_row = 4 if colour == "W" else 3
                self.tiles[taken_row][targ_col] = ""
            self.tiles[targ_row][targ_col] = proposed_move[0] + colour
            # Another special case, of promotion
            if proposed_move[-2] == "=":
                self.tiles[targ_row][targ_col] = proposed_move[-1] + colour
        # Final updates to internal state
        self.last_move = proposed_move
        self.update_castle_list()
        self.current_player = other_player[colour]
        if "KW" not in self.tiles.flatten():
            self.outcome = "B wins"
        if "KB" not in self.tiles.flatten():
            self.outcome = "W wins"

    def run_move(self):
        poss_moves = self.get_all_possible_moves(self.current_player)
        imp_moves = []
        while True:
            self.send_info_to_player(
                self.players[self.current_player],
                poss_moves,
                imp_moves
            )
            proposed_move = self.get_move_from_player(
                self.players[self.current_player]
            )
            if proposed_move not in poss_moves:
                print("Not a possible move!")
                continue
            move_succeeds = np.random.uniform(0, 1) > 0.5
            if move_succeeds:
                print(f"Flip succeeds! {proposed_move} accepted")
                break
            else:
                print(f"Flip fails! {proposed_move} rejected")
                poss_moves.remove(proposed_move)
                imp_moves.append(proposed_move)
                if len(poss_moves) == 0:
                    print(f"{self.current_player} cannot move, and loses")
                    self.outcome = f"{other_player[self.current_player]} wins"
                    return
                continue
        self.process_move(proposed_move)

    def play(self):
        while True:
            self.run_move()
            self.display_tiles()
            if f"K{self.current_player}" not in self.tiles.flatten():
                print(f"King taken! {self.current_player} loses!")
                self.outcome = f"{self.current_player} wins"
                return
            elif len(self.outcome) > 0:
                return
