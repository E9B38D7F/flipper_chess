#include <vector> // For vectors
#include <cstdlib> // For abs
#include <iostream> // For std::cout
#include <algorithm> // For finding children with best prob; other bits too
#include <chrono> // For timing the thinking loop
#include <pybind11/pybind11.h> // For python integration
#include <pybind11/stl.h>


#define KING 3000
#define QUEEN 900
#define ROOK 500
#define BISHOP 300
#define KNIGHT 299
#define PAWN 100

// BLOCK 1: Move generation
using BoardState = std::array<int, 70>; // Let's make things readable

std::vector<BoardState> get_king_moves(
    BoardState bs, int si
) {
    std::vector<BoardState> outcomes {};
    std::array<int, 8> increments {-9, -8, -7, -1, 1, 7, 8, 9};
    for (int inc : increments) {
        int ti {si + inc}; // index of target square
        if (ti < 0 || ti > 63) continue; // i.e., move off bottom or top
        if (std::abs(ti % 8 - si % 8) == 7) continue; // i.e., wrap around
        if (bs[ti] * (1 - 2 * bs[69]) > 0) continue; // occupied by own piece
        BoardState new_board = bs;
        new_board[si] = 0; // clear old square
        new_board[ti] = KING * (1 - 2 * (bs[69])); // king on new square
        new_board[64 + 2 * bs[69]] = 0; // delete own castling possibilities
        new_board[65 + 2 * bs[69]] = 0;
        new_board[68] = -1; // can't do en passant after a king move
        outcomes.push_back(new_board);
    }
    return outcomes;
}

std::vector<BoardState> get_rook_moves(
    BoardState bs, int si, int piece
) {
    std::vector<BoardState> outcomes {};
    std::array<int, 4> dirs {-8, -1, 1, 8};
    for (int dir : dirs) {
        int ti {si};
        while (true) {
            ti = ti + dir;
            if (ti < 0 || ti > 63) break;
            if (std::abs(ti % 8 - (ti - dir) % 8) > 1) break; // wraparound
            if (bs[ti] * (1 - 2 * bs[69]) > 0) break; // of own colour
            BoardState new_board = bs;
            new_board[si] = 0;
            new_board[ti] = piece * (1 - 2 * (bs[69]));
            new_board[68] = -1;
            outcomes.push_back(new_board);
            if (bs[ti] * (1 - 2 * bs[69]) < 0) break; // of other colour
        }
    }
    return outcomes;
}

std::vector<BoardState> get_bishop_moves(
    BoardState bs, int si, int piece
) {
    // Basically same structure as rook moves
    std::vector<BoardState> outcomes {};
    std::array<int, 4> dirs {-9, -7, 7, 9};
    for (int dir : dirs) {
        int ti {si};
        while (true) {
            ti = ti + dir;
            if (ti < 0 || ti > 63) break;
            if (std::abs(ti % 8 - (ti - dir) % 8) > 1) break; // wraparound
            if (bs[ti] * (1 - 2 * bs[69]) > 0) break;
            BoardState new_board = bs;
            new_board[si] = 0;
            new_board[ti] = piece * (1 - 2 * (bs[69]));
            new_board[68] = -1;
            outcomes.push_back(new_board);
            if (bs[ti] * (1 - 2 * bs[69]) < 0) break;
        }
    }
    return outcomes;
}

std::vector<BoardState> get_queen_moves(
    BoardState bs, int si
) {
    std::vector<BoardState> outcomes = get_rook_moves(bs, si, QUEEN);
    std::vector<BoardState> b_out = get_bishop_moves(bs, si, QUEEN);
    outcomes.insert(outcomes.end(), b_out.begin(), b_out.end());
    return outcomes;
}

std::vector<BoardState> get_knight_moves(
    BoardState bs, int si
) {
    // Basically same structure as king moves
    std::vector<BoardState> outcomes {};
    std::array<int, 8> increments {-17, -15, -10, -6, 6, 10, 15, 17};
    for (int inc : increments) {
        int ti {si + inc};
        if (ti < 0 || ti > 63) continue;
        if (std::abs(ti % 8 - si % 8) > 2) continue;
        if (bs[ti] * (1 - 2 * bs[69]) > 0) continue;
        BoardState new_board = bs;
        new_board[si] = 0;
        new_board[ti] = KNIGHT * (1 - 2 * (bs[69]));
        new_board[68] = -1;
        outcomes.push_back(new_board);
    }
    return outcomes;
}

std::vector<BoardState> get_pawn_moves(
    BoardState bs, int si
) {
    std::vector<BoardState> outcomes {};
    int dir {1 - 2 * (bs[69])};
    std::vector<int> pieces;
    // Catch promotion case
    int ti {si + dir * 8};
    if (ti / 8 == 0 or ti / 8 == 7) pieces = {QUEEN, ROOK, BISHOP, KNIGHT};
    else pieces = {PAWN};

    // Single step forward
    if (bs[ti] == 0) {
        for (int piece : pieces) {
            BoardState new_board = bs;
            new_board[si] = 0;
            new_board[ti] = piece * (1 - 2 * (bs[69]));
            new_board[68] = -1;
            outcomes.push_back(new_board);
        }
    }

    // Attacks
    std::array<int, 2> increments {7 * dir, 9 * dir};
    for (int inc : increments) {
        ti = si + inc;
        if (
            (std::abs(ti % 8 - si % 8) == 1) // no wraparound
            && (bs[ti] * dir < 0) // of opposite colour
            && (ti >= 0 && ti <= 63) // within the board
        ) {
            for (int piece : pieces) {
                BoardState new_board = bs;
                new_board[si] = 0;
                new_board[ti] = piece * (1 - 2 * (bs[69]));
                new_board[68] = -1;
                outcomes.push_back(new_board);
            }
        }
    }

    // Double step forward (plus en passant eligibility)
    if (
        ((bs[69] == 0 && si / 8 == 1) || (bs[69] == 1 && si / 8 == 6)) // rank
        && (bs[si + dir * 8] == 0) // next square unoccupied
        && (bs[si + dir * 16] == 0) // following square unoccupied
    ) {
        BoardState new_board = bs;
        new_board[si] = 0;
        new_board[si + dir * 16] = PAWN * (1 - 2 * (bs[69]));
        new_board[68] = si + dir * 8; // this is where en-passanter lands
        outcomes.push_back(new_board);
    }
    return outcomes;
}


std::vector<BoardState> get_square_moves(
    BoardState bs, int si
) {
    switch ((1 - 2 * (bs[69])) * bs[si]) {
        /* bs[69] is 0 if white to move, 1 if black to move
        so this flips signs of all pieces iff black to move */
        case KING:
            return get_king_moves(bs, si);
        case QUEEN:
            return get_queen_moves(bs, si);
        case ROOK:
            return get_rook_moves(bs, si, ROOK);
        case BISHOP:
            return get_bishop_moves(bs, si, BISHOP);
        case KNIGHT:
            return get_knight_moves(bs, si);
        case PAWN:
            return get_pawn_moves(bs, si);
    }
    return std::vector<BoardState> {};
}


std::vector<BoardState> get_poss_board_states(
    BoardState bs
) {
    // Returns every possible board state that can be reached in one move
    std::vector<BoardState> outcomes {};

    // Iterate over tiles, get moves for each piece on the tile
    for (int i {0}; i < 64; i++) {
        for (BoardState ns : get_square_moves(bs, i)) {
            outcomes.push_back(ns);
        }
    }

    // Castling
    int dir {1 - 2 * (bs[69])};
    int base {56 * (bs[69])}; // offset for black back rank
    if ( // kingside castling
        bs[65 - dir] == 1 // i.e., have permission to castle
        && bs[base + 4] == KING * dir // then check the pieces are placed right
        && bs[base + 5] == 0
        && bs[base + 6] == 0
        && bs[base + 7] == ROOK * dir
    ) {
        BoardState new_board = bs;
        new_board[base + 4] = 0;
        new_board[base + 5] = ROOK * dir;
        new_board[base + 6] = KING * dir;
        new_board[base + 7] = 0;
        new_board[64 + 2 * bs[69]] = 0;
        new_board[65 + 2 * bs[69]] = 0;
        new_board[68] = -1;
        outcomes.push_back(new_board);
    }
    if (
        bs[66 - dir] == 1
        && bs[base] == ROOK * dir // queenside
        && bs[base + 1] == 0
        && bs[base + 2] == 0
        && bs[base + 3] == 0
        && bs[base + 4] == KING * dir
    ) {
        BoardState new_board = bs;
        new_board[base] = 0;
        new_board[base + 1] = 0;
        new_board[base + 2] = KING * dir;
        new_board[base + 3] = ROOK * dir;
        new_board[base + 4] = 0;
        new_board[64 + 2 * bs[69]] = 0;
        new_board[65 + 2 * bs[69]] = 0;
        new_board[68] = -1;
        outcomes.push_back(new_board);
    }

    // En passant
    if (bs[68] != -1) {
        std::array<int, 2> dep_idxs {bs[68] - 7 * dir, bs[68] - 9 * dir};
        for (int dep_idx : dep_idxs) {
            if (
                (bs[dep_idx] * dir == PAWN)
                && (std::abs(bs[68] % 8 - dep_idx % 8) == 1)
            ) {
                BoardState new_board = bs;
                new_board[dep_idx] = 0;
                new_board[bs[68]] = PAWN * dir;
                new_board[bs[68] - 8 * dir] = 0; // delete pawn getting taken
                new_board[68] = -1;
                outcomes.push_back(new_board);
            }
        }
    }

    for (BoardState& outcome : outcomes) {
        // 1. Update castle opportunities
        if (outcome[0] != ROOK) outcome[65] = 0;
        if (outcome[4] != KING) {outcome[64] = 0; outcome[65] = 0;}
        if (outcome[7] != ROOK) outcome[64] = 0;
        if (outcome[56] != -ROOK) outcome[67] = 0;
        if (outcome[60] != -KING) {outcome[66] = 0; outcome[67] = 0;}
        if (outcome[63] != -ROOK) outcome[66] = 0;
        // 2. Switch whose turn it is
        outcome[69] = 1 - outcome[69];
    }
    return outcomes;
}



// BLOCK 2: Thinkin

class ThinkingNode{
public:
    ThinkingNode* parent {};
    std::vector<ThinkingNode*> children {};
    BoardState board {};
    double eval;
    double prob;
    bool marked {true}; // Used in ThinkingMachine for uppropagate
    bool leaf {true};

    ThinkingNode() = default;
    ThinkingNode(ThinkingNode* par, BoardState boa) {
        this->parent = par;
        this->board = boa; // NOTE: maybe better off not to copy-initialise?
        this->update_eval();
    }

    ~ThinkingNode() {
        for (ThinkingNode* child : children) delete child;
    }

    ThinkingNode* get_highest_prob_leaf() {
        if (children.size() == 0) return this;

        ThinkingNode* best_leaf = nullptr;
        double best_prob = -1.0;
        for (ThinkingNode* child : children) {
            ThinkingNode* leaf = child->get_highest_prob_leaf();
            if (leaf->prob > best_prob) {
                best_prob = leaf->prob;
                best_leaf = leaf;
            }
        }
        return best_leaf;
    }

    void update_eval() {
        /* Sets own score by taking weighted mean of child scores
        Which is 1/2 * [best one] + 1/4 * [next best] + ... */
        if (children.size() == 0) {
            eval = 0;
            for (int i {0}; i < 64; i++) eval += board[i];
            // std::cout << "\t\tleaf node eval: " << eval << "\n";
            return;
        }
        std::sort(
            children.begin(),
            children.end(),
            [this](const ThinkingNode* a, const ThinkingNode* b) {
                if (this->board[69] == 0) {
                    return a->eval > b->eval; // Descending if white
                } else {
                    return a->eval < b->eval; // Ascending if black
                }
            }
        );
        eval = 0;
        double weight {1.0};
        for (int i {0}; i < children.size(); i++){
            weight /= 2;
            eval += weight * children[i]->eval;
        }
        eval += weight * 3000 * (1 - 2 * board[69]); // If out of moves
        // std::cout << "\tinterior node eval: " << eval << "\n";
    }

    void update_probs() {
        /* Sets probabilities such that best move is most likely to get played
        and so on, in preference order.
        Note that this recurses on children */
        std::sort(
            children.begin(),
            children.end(),
            [this](const ThinkingNode* a, const ThinkingNode* b) {
                if (this->board[69] == 0) {
                    return a->eval > b->eval; // Descending if white
                } else {
                    return a->eval < b->eval; // Ascending if black
                }
            }
        );
        double weight {1.0};
        for (int i {0}; i < children.size(); i++) {
            weight /= 2;
            children[i]->prob = prob * weight;
            children[i]->update_probs();
        }
    }

    void create_children() {
        /* Create a child for every possible move
        and gives them all the relevant info */
        std::vector<BoardState> pbss = get_poss_board_states(board);
        for (BoardState pbs : pbss) {
            ThinkingNode* new_one = new ThinkingNode(this, pbs);
            children.push_back(new_one);
        }
        ThinkingNode* curr_node = this;
        while (curr_node != nullptr) {
            curr_node->update_eval();
            curr_node = curr_node->parent;
        }
    }
};


class ThinkingMachine {
public:
    ThinkingNode root {};
    std::vector<ThinkingNode*> leaves {};
    int size {1}; // just out of curiosity
    int max_size {};

    ThinkingMachine() = default;
    ThinkingMachine(BoardState bs, int ms) {
        this->root = ThinkingNode(nullptr, bs);
        this->root.prob = 1;
        this->max_size = ms;
        // this->max_size = 100000000;
        leaves.push_back(&root);
    }

    std::vector<ThinkingNode*> get_highest_prob_leaves(int n) {
        if (n == leaves.size()) return leaves;
        // Do nth element kind-of-sort
        std::nth_element(
            leaves.begin(),
            leaves.begin() + n,
            leaves.end(),
            [](const ThinkingNode* a, const ThinkingNode* b) {
                return a->prob > b->prob;
            }
        );
        // Then truncate to get just the first n
        return std::vector<ThinkingNode*>(leaves.begin(), leaves.begin() + n);
    }

    bool add_children_to_leaf(ThinkingNode* leaf) {
        /* Adds all children to a given leaf
        returns false if it hits maximum number of nodes; true otherwise
        (interpret the return value as "keep going", false says stop) */
        // Get possible moves
        std::vector<BoardState> pbss = get_poss_board_states(leaf->board);
        for (BoardState pbs: pbss) {
            if (size > max_size) return false;
            // Make a new leaf for each one
            ThinkingNode* new_one = new ThinkingNode(leaf, pbs);
            leaf->children.push_back(new_one);
            leaves.push_back(new_one);
            size += 1;
        }
        leaf->leaf = false;
        // Now make sure to mark ancestors as needing eval update
        ThinkingNode* curr_node = leaf;
        while ((curr_node != nullptr) && (!curr_node->marked)) {
            curr_node->marked = true;
            curr_node = curr_node->parent;
        }
        return true;
    }

    void uppropagate_evals(ThinkingNode* node) {
        // Updates evals for all the marked nodes, bottom-up
        // Base case: it's a leaf, so just add material on the board
        if (node->leaf) {
            node->eval = 0;
            for (int i {0}; i < 64; i++) node->eval += node->board[i];
            node->marked = false;
            return;
        }
        // Recurse on children first, to make sure they are all updated
        for (ThinkingNode* child : node->children) {
            if (child->marked) {
                this->uppropagate_evals(child);
                child->marked = false;
            }
        }
        // Then aggregate children
        std::sort(
            node->children.begin(),
            node->children.end(),
            [node](const ThinkingNode* a, const ThinkingNode* b) {
                if (node->board[69] == 0) {
                    return a->eval > b->eval; // Descending if white
                } else {
                    return a->eval < b->eval; // Ascending if black
                }
            }
        );
        node->eval = 0;
        double weight {1.0};
        for (int i {0}; i < node->children.size(); i++){
            weight /= 2;
            node->eval += weight * node->children[i]->eval;
        }
        node->eval += weight * 3000 * (1 - 2 * node->board[69]);
        node->marked = false;
    }

    void update_probs(ThinkingNode* node) {
        /* Updates play probabilities for all nodes, top down
        Note it's already called after children are sorted
        (implemented as a DFS because that has same effect) */
        double weight {1.0};
        for (int i {0}; i < node->children.size(); i++) {
            weight /= 2;
            node->children[i]->prob = node->prob * weight;
            this->update_probs(node->children[i]);
        }
    }

    void clean_leaves() {
        // Remove from leaves everything that is no longer a leaf
        auto new_end = std::remove_if(
            leaves.begin(),
            leaves.end(),
            [](const ThinkingNode* node) {return !node->leaf;}
        );
        leaves.erase(new_end, leaves.end());
    }

    bool expand_frac_leaves(float frac) {
        // 1. Find which leaves to expand
        int n {static_cast<int>(std::ceil(frac * leaves.size()))};
        if (n < 100) n = 100;
        if (n > leaves.size()) n = leaves.size();
        if (n > 50000) n = 50000; // Don't get too wide!
        std::vector<ThinkingNode*> expandenda = get_highest_prob_leaves(n);
        std::cout << expandenda.size() << "\n";
        // 2. Make them children
        for (ThinkingNode* exp : expandenda) {
            bool still_under_size {add_children_to_leaf(exp)};
            if (!still_under_size) {std::cout << "hit size\n"; return false;}
        }
        // 3. Uppropagate
        this->uppropagate_evals(&root);
        // 4. Fix probabilities
        this->update_probs(&root);
        // 5. Keep the list of leaves in order
        this->clean_leaves();
        return true;
    }
};


std::vector<std::pair<BoardState, double>> think_dep(BoardState bs, int time) {
    /*
    Note: this is deprecated think() method
    THE function that matters
    takes in a given board state (and how many seconds it can think)
    returns all possible board states that can result from that
    with their evals */
    // Step 1: Have a bit of a think
    ThinkingNode think_root {nullptr, bs};
    think_root.prob = 1;
    auto start = std::chrono::steady_clock::now();
    auto end = start + std::chrono::seconds(time);
    int counter {0};
    while (std::chrono::steady_clock::now() < end) {
        ThinkingNode* look_node = think_root.get_highest_prob_leaf();
        look_node->create_children();
        think_root.update_probs();
        counter += 1;
    }
    std::cout << "num nodes: " << counter << "\n";
    // Step 2: Share thoughts with the rest of us
    std::vector<std::pair<BoardState, double>> outcomes;
    for (ThinkingNode* child : think_root.children) {
        outcomes.push_back({child->board, child->eval});
    }
    return outcomes;
}


std::vector<std::pair<BoardState, double>> think(
    BoardState bs, int time, int max_nodes
) {
    /* This one is not deprecated
    Includes a few efficiencies on the above algo
    mainly batching together operations that require iterating over
    the entire game tree, so do far fewer traversals
    NOTE: time is in millis now max_nodes=4m is about right */
    float frac {0.1};
    ThinkingMachine think_machine {bs, max_nodes};
    auto start = std::chrono::steady_clock::now();
    auto end = start + std::chrono::milliseconds(time);
    bool not_full {true};
    while ((std::chrono::steady_clock::now() < end) && not_full) {
        not_full = think_machine.expand_frac_leaves(frac);
    }
    std::cout << "num nodes: " << think_machine.size << "\n";
    std::vector<std::pair<BoardState, double>> outcomes;
    for (ThinkingNode* child : think_machine.root.children) {
        outcomes.push_back({child->board, child->eval});
    }
    return outcomes;
}



// Now things so it can be called in python

namespace py = pybind11;

PYBIND11_MODULE(my_module, m) {
    // First one just in for bug testing, second one is the useful one
    m.def("get_outcomes", &get_poss_board_states, "Gets poss board states");
    m.def("think", &think, "Does the thinking");
}


// Below here is for bugfixing: look at output for a given board


// int main() {
//      BoardState start {
//          0, 299, 0, 0, 3000, 300, -900, 500,
//         -100, 0, 100, 0, 900, 0, 100, 0,
//         0, 0, 0, 0, 0, 0, 0, 100,
//         100, 0, 0, 0, 0, 100, 0, -100,
//         -100, 0, 0, 100, 0, 0, 0, 0,
//         0, 0, 0, 0, 0, 0, -100, -299,
//         0, -100, 0, 0, -100, -100, -300, 0,
//         0, 0, -500, 0, -3000, 0, -500, 0,
//         1, 0, 0, 0, -1, 1
//     };
//     std::vector<BoardState> outcomes = get_poss_board_states(start);
//     for (BoardState outcome : outcomes) {
//         for (int item : outcome) std::cout << item << ", ";
//         std::cout << "\n";
//     }
// }
