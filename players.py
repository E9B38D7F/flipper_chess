import numpy as np
import time
import random
from evals import (
    generate_complex_eval_dict,
    get_board_score_with_position,
    get_board_score_with_mobility
)
import pandas as pd
import torch


import my_module


class Player:
    def __init__(self, colour):
        self.colour = colour
    def receive_info(self, board, possible_moves, imp_moves, new_board=True):
        return
    def send_move(self):
        return



class BozoBot(Player):
    # Randomly chooses a move

    def __init__(self, colour):
        super().__init__(colour)
        self.possible_moves = []

    def receive_info(self, board, possible_moves, imp_moves, new_board=True):
        self.possible_moves = possible_moves
        # Below is (deprecated) module used for bug testing the cpp unit
        # if new_board:
        #     # This is running checks that cpp is fine
        #     # 1. Get module outputs for poss board states
        #     cpp_df = pd.DataFrame(
        #         my_module.get_outcomes(board.export())
        #     ).sort_values(by=[i for i in range(70)]).reset_index(drop=True)
        #     # 2. Get outputs from board
        #     py_df = pd.DataFrame([
        #         board.copy().process_move(move, colour=self.colour).export()
        #         for move in possible_moves
        #     ]).sort_values(by=[i for i in range(70)]).reset_index(drop=True)
        #     # 3. Compare
        #     outcome = abs(cpp_df - py_df).sum().sum()
        #     if outcome != 0:
        #         cpp_df.to_csv("../cpp_df.csv", index=False)
        #         py_df.to_csv("../py_df.csv", index=False)
        #         print([int(i) for i in board.export()])
        #         assert False
        #     print("outcome 0")


    def send_move(self):
        return random.choice(self.possible_moves)


class CppBot(Player):
    # Uses the cpp tree search algo
    def __init__(self, colour, thinking_time, max_tree_size):
        super().__init__(colour)
        self.poss_moves = []
        self.preferences = None
        self.thinking_time = thinking_time
        self.max_tree_size = max_tree_size

    def receive_info(self, board, poss_moves, imp_moves, new_board=True):
        self.poss_moves = poss_moves
        if new_board:
            rs = my_module.think(
                board.export(),
                self.thinking_time,
                self.max_tree_size
            )
            board_map = dict(zip([str(r[0]) for r in rs], [r[1] for r in rs]))
            move_map = {
                move: str([
                    int(i) # To make "np.int(3)" appear as "3"
                    for i in board.copy().process_move(
                        move, colour=self.colour
                    ).export()
                ])
                for move in self.poss_moves
            }
            prefs = {move: board_map[move_map[move]] for move in poss_moves}
            self.preferences = pd.Series(prefs) / 100
        self.preferences = self.preferences.loc[poss_moves].sort_values(
            ascending=self.colour == "B"
        )
        print(self.preferences)

    def send_move(self):
        top_move = self.preferences.index[0]
        self.preferences = self.preferences.iloc[1:]
        return top_move


class DeepBot(Player):
    # Template for general neural net play
    # They differ in their think() methods, so leave that empty

    def __init__(self, colour, model_filepath):
        super().__init__(colour)
        self.model = torch.load(model_filepath, weights_only=False)
        self.model.eval()
        self.possible_moves = []
        self.sorted_moves = []
        self.board = None

    def receive_info(self, board, possible_moves, imp_moves, new_board=True):
        self.board = board
        self.possible_moves = possible_moves
        if new_board:
            self.think()

    def send_move(self):
        top_pref = self.sorted_moves[0]
        self.sorted_moves = self.sorted_moves[1:]
        return top_pref

    def think(self):
        return None


class AutoDeep(DeepBot):
    # Uses a pre-trained neural net to do the thinking
    # Doesn't explore any paths, just evals board which results from each move
    def think(self):
        temp_tens = torch.tensor(
            [
                self.board.copy().process_move(
                    move, colour=self.colour
                ).export()
                for move in self.possible_moves
            ],
            dtype=torch.float32
        ) # next line is to delete en passant data...
        board_tensor = torch.cat([temp_tens[:, :68], temp_tens[:, 69:]], dim=1)
        predictions = self.model(board_tensor).cpu().detach().numpy()[:,0]
        order = -1 if self.colour == "W" else 1
        sorted_indices = np.argsort(predictions)[::order]
        self.sorted_moves = [self.possible_moves[i] for i in sorted_indices]


class FlatBot(DeepBot):
    # Also a pre-trained neural net
    # But this is one that has a one-hot encoding of board structure
    # So hopefully plays better
    def think(self):
        def get_big_tensor(array):
            """
            Transforms each row into a 13x8x8 tensor
            13 correspond to empty, wpawn, ..., wking, bpawn, ..., bking
            then the 8x8 is the board
            all these together are returned as a (len_df)x13x8x8 tensor
            (copypasted from model training notebook)
            """
            np_output = np.zeros((len(array), 13, 8, 8), dtype=np.bool_)
            for piece_val, board_num in zip(
                [0, 1, 2, 3, 4, 5, 6, -1, -2, -3, -4, -5, -6], range(13)
            ):
                mask = (array == piece_val)
                np_output[:, board_num, :, :] = mask.reshape(len(array), 8, 8)
            return torch.from_numpy(np_output)
        temp_array = np.array([
            self.board.copy().process_move(move, colour=self.colour).export()
            for move in self.possible_moves
        ])
        board_tensor = get_big_tensor(temp_array[:, :64]).flatten(-3).float()
        with torch.no_grad():
            predictions = self.model(board_tensor).cpu().detach().numpy()[:,0]
        order = -1 if self.colour == "W" else 1
        sorted_indices = np.argsort(predictions)[::order]
        self.sorted_moves = [self.possible_moves[i] for i in sorted_indices]



class OneLayer(Player):
    # Structure is basically a copypaste of AutoDeep
    # But instead of a neural net, it just adds up material on the board
    # Does the move that takes the most material
    # Not the smartest, but might beat the neural net

    def __init__(self, colour):
        super().__init__(colour)
        self.possible_moves = []
        self.sorted_moves = []
        self.board = None

    def receive_info(self, board, possible_moves, imp_moves, new_board=True):
        self.board = board
        self.possible_moves = possible_moves

    def send_move(self):
        self.think() # ehh double up for now, who cares
        top_pref = self.sorted_moves[0]
        self.sorted_moves = self.sorted_moves[1:]
        return top_pref

    def think(self):
        points_dict = {
            "KW": 30, "QW": 9, "RW": 5, "BW": 3, "NW": 3, "PW": 1,
            "KB": -30, "QB": -9, "RB": -5, "BB": -3, "NB": -3, "PB": -1,
            "": 0
        }
        predictions = np.array([
            np.vectorize(
                points_dict.__getitem__
            )(
                self.board.copy().process_move(move, colour=self.colour).tiles
            ).sum().sum()
            for move in self.possible_moves
        ])
        order = -1 if self.colour == "W" else 1
        sorted_indices = np.argsort(predictions)[::order]
        self.sorted_moves = [self.possible_moves[i] for i in sorted_indices]


class HumanPlayer(Player):
    # Play by manually inputting moves

    def __init__(self, colour):
        super().__init__(colour)

    def receive_info(self, board, possible_moves, imp_moves):
        print(f"Last move: {board.last_move}")
        private_board = board.copy()
        private_board.display_tiles(colour=self.colour)
        if len(imp_moves) > 0:
            print(f"Disallowed moves: {imp_moves}")

    def send_move(self):
        return None # oops shitty workaround, fix later



class TargetedTree(Player):

    def __init__(self, colour, think_time, search_const, eval_func, succ_prob):
        super().__init__(colour)
        self.think_time = think_time
        self.search_const = search_const # best move has this prob of play
        self.play_const = succ_prob
        self.eval_func = eval_func
        self.poss_moves = None
        self.thinking_tree_root = None
        self.board = None

    def receive_info(self, board, poss_moves, imp_moves, new_board=True):
        if self.board is not None:
            if not np.all(board.tiles == self.board.tiles): # i.e., new board
                self.thinking_tree_root = None
        self.board = board.copy()
        self.poss_moves = poss_moves

    def send_move(self):
        if self.thinking_tree_root is None:
            self.think()
        prioritised_moves = sorted(
            self.poss_moves,
            key=lambda x: self.thinking_tree_root.children[x].eval,
            reverse=self.colour == "W" # want high evals if white
        )
        return prioritised_moves[0]

    def think(self):
        self.thinking_tree_root = ThinkingNode(
            None,
            self.board,
            self.colour,
            self.search_const,
            self.play_const,
            generate_complex_eval_dict(),
            self.eval_func
        )
        self.thinking_tree_root.search_prob = 1
        self.thinking_tree_root.play_prob = 1
        start = time.time()
        while time.time() - start < self.think_time:
            look_node = self.thinking_tree_root.get_highest_prob_leaf_below()
            look_node.create_children()
            self.thinking_tree_root.update_probs()


class ThinkingNode:

    def __init__(
        self,
        parent,
        board,
        colour,
        search_const,
        play_const,
        eval_dict,
        eval_func
    ):
        self.parent = parent
        self.children = {}
        self.board = board
        self.colour = colour
        self.search_const = search_const
        self.play_const = play_const
        self.search_prob = None
        self.play_prob = None
        self.eval_dict = eval_dict
        self.eval_func = eval_func
        self.eval = eval_func(self.board, self.eval_dict)
        # self.eval = get_board_score_material_only(self.board)

    def print_self_and_all_below(self, inherited):
        print_line = inherited
        print_line += f", search_prob {self.search_prob:.5f}"
        print_line += f", play_prob {self.play_prob:.5f}"
        print_line += f", eval {self.eval:.2f}"
        print(print_line)
        sorted_children_keys = sorted(
            self.children.keys(),
            key=lambda key: -self.children[key].play_prob, # minus to reverse
        )
        for key in sorted_children_keys:
            self.children[key].print_self_and_all_below(f"  {inherited} {key}")

    def get_highest_prob_leaf_below(self):
        """ Returns a ThinkingNode """
        if len(self.children) == 0:
            return self
        return max(
            [
                child.get_highest_prob_leaf_below()
                for child in self.children.values()
            ],
            key=lambda x: x.search_prob
        )

    def update_eval(self):
        """ Updates eval only on this one node """
        if len(self.children) == 0:
            return # already calculated in constructor!
        sorted_child_evals = sorted(
            [child.eval for child in self.children.values()],
            reverse=self.colour == "W"
        ) # THEN add in no moves -> auto loss
        sorted_child_evals.append(-100 if self.colour == "W" else 100)
        weights = self.play_const ** np.arange(1, len(self.children) + 2, 1)
        weights[-1] = 1 - weights[:-1].sum() # make them sum to 1
        self.eval = (np.array(sorted_child_evals) * weights).sum()

    def update_probs(self):
        """ Updates probs for this node and all descendants """
        sorted_children = sorted(
            self.children.values(),
            key=lambda x: x.eval,
            reverse=self.colour == "W"
        )
        for child, index in zip(sorted_children, range(1, 10**10)):
            child.search_prob = (
                (1 - self.search_const) ** index
                * self.search_prob
                * self.search_const / (1 - self.search_const)
            )
            child.play_prob = (
                (1 - self.play_const) ** index
                * self.play_prob
                * self.play_const /  (1 - self.play_const)
            )
        for child in sorted_children:
            child.update_probs()

    def create_children(self):
        poss_moves = self.board.get_all_possible_moves(self.colour)
        for move in poss_moves:
            new_board = self.board.copy()
            new_board.process_move(move, colour=self.colour)
            self.children[move] = ThinkingNode(
                self,
                new_board,
                {"B": "W", "W": "B"}[self.colour],
                self.search_const,
                self.play_const,
                self.eval_dict,
                self.eval_func
            )
        curr_node = self
        while curr_node is not None:
            curr_node.update_eval()
            curr_node = curr_node.parent
