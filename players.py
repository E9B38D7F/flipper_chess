import numpy as np
import time
from evals import (
    generate_complex_eval_dict,
    get_board_score_with_position,
    get_board_score_with_mobility
)



class Player:
    def __init__(self, colour):
        self.colour = colour
    def receive_info(self, board, possible_moves, imp_moves):
        return
    def send_move(self):
        return



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

    def receive_info(self, board, poss_moves, imp_moves):
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
