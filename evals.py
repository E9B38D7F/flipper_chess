import numpy as np


def get_board_score_material_only(board, dummy):
    """
    Simple as: sum up the pieces on the board and continue
    """
    points_dict = {
        "KW": 30, "QW": 9, "RW": 5, "BW": 3, "NW": 3, "PW": 1,
        "KB": -30, "QB": -9, "RB": -5, "BB": -3, "NB": -3, "PB": -1,
        "": 0
    }
    points = np.vectorize(points_dict.__getitem__)(board.tiles).sum().sum()
    return points


def get_board_score_with_mobility(board, dummy):
    """
    Eval function here is material PLUS some evaluation of mobility
    Here it's the number of possible moves a player can make / 100
    (i.e., won't be killing pawns to get mobility, mostly tiebreaker)
    """
    base_score = get_board_score_material_only(board, None)
    num_white_moves = len(board.get_all_possible_moves("W"))
    num_black_moves = len(board.get_all_possible_moves("B"))
    return base_score + (num_white_moves - num_black_moves) / 100


def get_board_score_with_hanging(board, dummy):
    """
    Treats hanging pieces as though they have sort of been taken already
    """
    base_score = get_board_score_material_only(board, None)
    def get_value_hanging(colour):
        points_dict = {
            "KW": 30, "QW": 9, "RW": 5, "BW": 3, "NW": 3, "PW": 1,
            "KB": -30, "QB": -9, "RB": -5, "BB": -3, "NB": -3, "PB": -1,
            "": 0
        }
        squares_under_attack = {
            move.split("x")[1][:2]
            for move in board.get_all_possible_moves(other_player[colour])
            if "x" in move
        }
        value_under_attack = sum(
            [points_dict[board.tiles[bta(square)]]
            for square in squares_under_attack]
        )
        return -value_under_attack # Black hanging is good for White, etc.
    white_value_hanging = get_value_hanging("W")
    black_value_hanging = get_value_hanging("B")
    return base_score + (white_value_hanging - black_value_hanging) / 4


def generate_complex_eval_dict():
    """ Method used to generate dict for get_board_score_with_position """
    def evaluate_square(colour, piece, centrality, rank):
        # Used for
        if piece == "K": # Want to keep king away from the middle
            return colour_mult_dict[colour] * (
                base_vals_dict[piece] - centrality_dict[centrality]
            )
        elif piece == "P": # Want to push pawns up the board
            if colour == "W":
                return base_vals_dict[piece] + (
                    rank_dict[rank] - rank_dict["2"]
                ) # i.e., +10 centipawns per rank advanced
            else:
                return - base_vals_dict[piece] + (
                    rank_dict[rank] - rank_dict["7"]
                )
        else: # Want other pieces in the middle; proxy for mobility
            return colour_mult_dict[colour] * (
                base_vals_dict[piece] + centrality_dict[centrality] / 6
            ) # i.e., 2pt diff between being on rim and right in centre
    base_vals_dict = {"K": 40, "Q": 9, "R": 5, "B": 3, "N": 3, "P": 1}
    colour_mult_dict = {"W": 1, "B": -1}
    centrality_dict = {"0": 0, "1": 0.1, "2": 0.2, "3": 0.3}
    rank_dict = {str(i): (i - 1) / 10 for i in range(1, 9)}
    complex_eval_dict = {
        f"{piece}{colour}{centrality}{rank}":
        evaluate_square(colour, piece, centrality, rank)
        for colour in "BW"
        for piece in "KQRBNP"
        for centrality in "0123" for
        rank in "12345678"
    }
    for centrality in "0123": # Fill in 0 for empty board spots
        for rank in "12345678":
            complex_eval_dict[centrality + rank] = 0
    return complex_eval_dict


def get_board_score_with_position(board, complex_eval_dict):
    """
    Modifies material only board score
    By weighting some squares more for some pieces,
    e.g., central ones more for knights
    """
    def gridify(lst): return np.array(list(lst)).reshape(8, 8)
    centrality = gridify(
        "0000000001111110012222100123321001233210012222100111111000000000"
    )
    ranks = gridify(
        "1111111122222222333333334444444455555555666666667777777788888888"
    )
    info_board = np.char.add(board.tiles, np.char.add(centrality, ranks))
    evaluations = np.vectorize(complex_eval_dict.__getitem__)(info_board)
    score = evaluations.sum().sum()
    return score
