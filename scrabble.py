import os
import sys
import enum
import random
import time

# Letter frequency
_FREQ = [9, 2, 2, 4, 12,
         2, 3, 2, 9, 1,
         1, 4, 2, 6, 8,
         2, 1, 6, 4, 6,
         4, 2, 2, 1, 2, 1]
# _LETTER_SCORE = [13 - f for f in _FREQ] # TODO!!!
_LETTER_SCORE = [1, 3, 3,  2, 1, 4,  2, 4, 1,
                 8, 5, 1,  3, 1, 1,  3, 10, 1,
                 1, 1, 1,  4, 4, 8,  3, 10]
print(_LETTER_SCORE)

Multiplier = enum.Enum('Multiplier',
                            names=[
                                'NONE',
                                'DOUBLE_LETTER',
                                'TRIPLE_LETTER',
                                'DOUBLE_WORD',
                                'TRIPLE_WORD'])

def choose_n(items, n, start=0):
  for k in range(start, len(items) - (n - 1)):
    if n > 1:
      for other in choose_n(items, n - 1, k + 1):
        yield tuple([k] + list(other))  # This is a bit inefficient
    else:
      yield (k,)


# Board has tripple word every 7 (except for center)
class Board:
    def __init__(self, dict_hash, num_players):
        self.random = random.Random()
        board = []
        for i in range(0, 15):
            row = [Multiplier.NONE for i in range(0, 15)]
            board.append(row)

        state = []
        for i in range(0, 15):
            row = [' ' for i in range(0, 15)]
            state.append(row)

        # Diagonals are double word
        for i in range(0, 15):
            board[i][i] = Multiplier.DOUBLE_WORD
            board[14 - i][i] = Multiplier.DOUBLE_WORD

        # Double letters
        for coord in [(0,3), (3, 0), (2, 6), (6, 2), (3, 7), (7, 3)]:
            board[coord[0]][coord[1]] = Multiplier.DOUBLE_LETTER
            board[coord[0]][14 - coord[1]] = Multiplier.DOUBLE_LETTER
            board[14 - coord[0]][coord[1]] = Multiplier.DOUBLE_LETTER
            board[14 - coord[0]][14 - coord[1]] = Multiplier.DOUBLE_LETTER

        # Triple letters
        for coord in [(0,5), (5, 0), (5, 5)]:
            board[coord[0]][coord[1]] = Multiplier.TRIPLE_LETTER
            board[coord[0]][14 - coord[1]] = Multiplier.TRIPLE_LETTER
            board[14 - coord[0]][coord[1]] = Multiplier.TRIPLE_LETTER
            board[14 - coord[0]][14 - coord[1]] = Multiplier.TRIPLE_LETTER

        for coord in [(0, 0), (0,7), (7, 0)]:
            board[coord[0]][coord[1]] = Multiplier.TRIPLE_WORD
            board[coord[0]][14 - coord[1]] = Multiplier.TRIPLE_WORD
            board[14 - coord[0]][coord[1]] = Multiplier.TRIPLE_WORD
            board[14 - coord[0]][14 - coord[1]] = Multiplier.TRIPLE_WORD

        self.board = board
        self.state = state
        self.num_played = 0
        self.dict_hash = dict_hash
        self.letters = [f for f in _FREQ]
        self.init_players(num_players)

    def init_players(self, num_players):
        self.players = [Player(self.draw_letters(7))
                        for _ in range(num_players)]

        # Swap the player with the longest word into the first position
        max_i = 0
        max_val = 0
        for pi, p in enumerate(self.players):
          words = self.dict_hash.find_all_words(p.letters)
          for word in words:
            if len(word) > max_val:
              max_i = pi
              max_val = len(word)

        if pi != 0:
          self.players[0], self.players[pi] = self.players[pi], self.players[0]
        
    def __str__(self):
        players = ['player[%d]: %s, score= %d' % (i, ''.join(player.letters), player.score)
                   for i, player in enumerate(self.players)]
        return '\n'.join(players) + '\n' + self.state_as_str()

    def state_as_str(self):
        return '\n'.join([''.join(row) for row in self.state])

    def print_board(self):
        print(str(self))

    def score_word(self, word, check=False):
        if check and not self.dict_hash.is_word(word):
            return 0
        score = 0
        for letter in word:
            score += _LETTER_SCORE[ord(letter) - ord('a')]
        return score

    def score_placed_word(self, i, j, direction, word):
        pos = [i, j]
        num_unknown = 0
        for k in range(len(word)):
            if max(pos[0], pos[1]) >= 15:
                return -1, -1
            s = self.state[pos[0]][pos[1]]
            if (s != ' ') and (s != word[k]):
                return -1, -1
            if s == ' ': num_unknown += 1
            pos[direction] += 1

        pos = [i, j]
        end_pos = [i, j]
        end_pos[direction] += (len(word) - 1)
        word_mult = 1

        prefix = self.trace_word(pos[0], pos[1], direction, word[0], suffix=False)
        suffix = self.trace_word(end_pos[0], end_pos[1], direction, word[-1], prefix=False)
        if prefix:
            prefix = prefix[:-1]
        if suffix:
            suffix = suffix[1:]
        pre_word = prefix + word + suffix
        #print('word, pre_word: %d, %d, [%s], [%s], %d' % (i, j, word, pre_word, direction))
        if not self.dict_hash.is_word(pre_word):
            # print('not a word')
            return -1, -1

        pre_score = self.score_word(prefix) + self.score_word(suffix)
        score = pre_score
        for k in range(len(word)):
            letter = word[k]
            letter_score = _LETTER_SCORE[ord(letter) - ord('a')]

            # Multipliers only apply to letters that are placed
            if self.state[pos[0]][pos[1]] == ' ':
                if self.board[pos[0]][pos[1]] == Multiplier.DOUBLE_LETTER:
                    letter_score *= 2
                if self.board[pos[0]][pos[1]] == Multiplier.TRIPLE_LETTER:
                    letter_score *= 3
                if self.board[pos[0]][pos[1]] == Multiplier.DOUBLE_WORD:
                    word_mult = 2
                if self.board[pos[0]][pos[1]] == Multiplier.TRIPLE_WORD:
                    word_multi = 3
            score += letter_score
            pos[direction] += 1
        word_score = score * word_mult

        # Need to check that we add onto an existing letter
        other_words_score = 0
        pos = [i, j]
        num_other_words = 0
        for k in range(len(word)):
            if self.state[pos[0]][pos[1]] == ' ':
                letters = self.trace_word(
                    pos[0], pos[1], 1 - direction, word[k])
                if len(letters) > 1:
                #    print('Word:', letters)
                    if not self.dict_hash.is_word(letters):
                        return -1, -1
                    other_words_score += self.score_word(letters)
                    num_other_words += 1
            pos[direction] += 1

        # TODO: num_other_words constraint is just a helper to keep results reasonable
        num_known = len(word) - num_unknown
        if self.num_played == 0:
          valid = (pos[1 - direction] == 7) and (end_pos[direction] >= 7) and (pos[direction] <= 7)
        else:
          valid = (other_words_score + pre_score + num_known) > 0 and (num_other_words <= 2)
        return word_score + other_words_score, valid

    def place_word(self, i, j, dir, word):
        pos = [i, j]
        for letter in word:
            self.state[pos[0]][pos[1]] = letter
            pos[dir] += 1

    def trace_word(self, i, j, direction, letter=None, prefix=True, suffix=True):
        if (i < 0) or (j < 0) or (i >= 15) or (j >= 15): return ''
        if not letter:
            letter = self.state[i][j]

        initial_pos = [i, j]
        pos = [i, j]
        if prefix:
            if pos[direction] > 0:
                pos[direction] -= 1
            while pos[direction] >= 0 and self.state[pos[0]][pos[1]] != ' ':
                pos[direction] -= 1
            if pos[direction] < 0:
                pos[direction] = 0
            if pos[direction] != initial_pos[direction] and (self.state[pos[0]][pos[1]] == ' '):
                pos[direction] += 1
        start = pos[direction]

        pos = [i, j]
        if suffix:
            if pos[direction] < 14:
                pos[direction] += 1
            while pos[direction] < 15 and self.state[pos[0]][pos[1]] != ' ':
                pos[direction] += 1
            if (pos[direction] >= 15):
                pos[direction] = 14
            if pos[direction] != initial_pos[direction] and (self.state[pos[0]][pos[1]] == ' '):
                pos[direction] -= 1
        end = pos[direction]

        pos = [i, j]
        pos[direction] = start
        w = []
        while pos[direction] <= end:
            if (i == pos[0]) and (j == pos[1]):
                w.append(letter)
            else:
                w.append(self.state[pos[0]][pos[1]])
            pos[direction] += 1
        return (''.join(w)).strip()


    def get_candidate_positions(self, letters):
        max_word = ''
        max_score = -1
        pos = []
        dir = 0
        valid_options = []
        print('num_played = %d' % self.num_played)
        if self.num_played == 0:
            col = 7
            words = self.dict_hash.find_all_words(letters)
            print('first_move')
            print(words)
            for w in words:
                for row in range(7 - len(w) + 1, 8):
                    score, _ = self.score_placed_word(row, col, dir, w)
                    if score > max_score:
                        max_score = score
                        pos = [row, col]
                        max_word = w
        else:
            # Try to use our own letters only
            for d in range(0, 2):
                for row in range(0, 15):
                    for col in range(0, 15):
                        subset = [' '] * (15 - (row if d == 0 else col))
                        p = [row, col]
                        for n in range(0, len(subset)):
                            subset[n] = self.state[p[0]][p[1]]
                            p[d] += 1

                        for n in range(2, len(subset)):
                            cons = subset[0:n]
                            extra_letters = []
                            for c in cons:
                                if c != ' ':
                                    extra_letters.append(c)
                            if not extra_letters: continue
                            t = time.time()
                            stats = {'calls': 0, 'checked': 0}
                            words = self.dict_hash.find_all_words_cons(letters, cons, stats)
                            elapsed = time.time() - t
                            if elapsed > 1:
                                print(len(words), time.time() - t,
                                      'letters = %s' % letters,
                                      'extra = %s' % extra_letters,
                                      'cons = %s' % cons, stats)
                            for w in words:
                                score, valid = self.score_placed_word(row, col, d, w)
                                #print('new:', row, col, d, w, score, max_score, '[' + ''.join(cons) + ']')
                                if valid and score > 0:
                                    valid_options.append((score, row, col, w))
                                if score > max_score and valid:
                                    max_score = score
                                    pos = [row, col]
                                    max_word = w
                                    dir = d

        valid_options.sort()
        print(valid_options[-10:-1])
        return max_score, max_word, pos, dir

    def draw_letters(self, n):
        num_letters = 0
        all_letters = []
        for i in range(len(self.letters)):
            num_letters += self.letters[i]
            all_letters += [chr(i + ord('a')) for _ in range(self.letters[i])]

        self.random.shuffle(all_letters)
        chosen, remaining = all_letters[0:n], all_letters[n:]
        self.letters = [0] * 26
        for l in remaining:
            self.letters[ord(l) - ord('a')] += 1
        return chosen

    def make_play(self, pi, pos, dir, word, max_score):
        hist = {}
        used_letters = 0
        for l in self.players[pi].letters:
            if l not in hist:
                hist[l] = 0
            hist[l] += 1
        for k in range(len(word)):
            if self.state[pos[0]][pos[1]] == ' ':
                hist[word[k]] -= 1
                used_letters += 1
                self.state[pos[0]][pos[1]] = word[k]
            pos[dir] += 1
        letters = []
        for h in hist:
            letters += [h] * hist[h]
        self.players[pi].letters = (letters +
                                    self.draw_letters(used_letters))
        self.players[pi].score += max_score
        self.num_played += 1

    def make_auto_play(self):
        pi = self.num_played % len(self.players)
        letters = ''.join(self.players[pi].letters)
        max_score, max_word, pos, dir = self.get_candidate_positions(
            self.players[pi].letters)
        print('Letters:', letters)
        print('Make play:', max_score, max_word, pos, dir)
        if max_score > 0:
            self.make_play(pi, pos, dir, max_word, max_score)
        return max_score > 0

    def done(self):
        for p in self.players:
            if len(p.letters) == 0:
                return True
        return False

class Player:
    def __init__(self, letters=[]):
        self.letters = letters
        self.score = 0

class DictHash:
    def __init__(self, filename, two_letters=None, three_letters=None):
        with open(filename, 'r') as f:
            words = [w.strip() for w in f.readlines()]

        words = list(filter(lambda x: len(x) > 1, words))

        if two_letters:
            with open(two_letters, 'r') as f:
                two_letters = set([w.strip().lower() for w in f.readlines()])
            stripped_words = []
            for word in words:
                if len(word) == 2 and (word not in two_letters):
                    continue
                stripped_words.append(word)
            words = stripped_words

        if three_letters:
            with open(three_letters, 'r') as f:
                three_letters = set([w.strip().lower() for w in f.readlines()])
            stripped_words = []
            for word in words:
                if len(word) == 3 and (word not in three_letters):
                    continue
                stripped_words.append(word)
            words = stripped_words


        self.words = words
        self.hash_to_index = {}
        for i in range(len(words)):
            h = self.hash(words[i])
            if h not in self.hash_to_index:
                self.hash_to_index[h] = []
            self.hash_to_index[h].append(i)

    def is_word(self, word):
        return word in self.find_words(word)

    def hash(self, word):
        count = [0] * 26
        letters = set()
        for w in word:
            c = ord(w.lower()) - ord('a')
            if c >= 0 and  c < 26:
                count[c] += 1
                letters.add(c)
        sum = 0
        for i in letters:
            sum = sum | ((0x3 & min(count[i], 3)) << (2 * i))
        return sum

    def find_words(self, letters):
        h = self.hash(letters)
        if h not in self.hash_to_index: return set()
        return set([self.words[i] for i in self.hash_to_index[h]])

    def find_all_words_cons(self, letters, constraint, stats):
        blanks = []
        non_blanks = []
        for i, letter in enumerate(constraint):
            if letter == ' ':
                blanks.append(i)
            else:
                non_blanks.append(letter)
        constrained_words = set()
        if len(blanks) == 0: return set()
        if len(letters) >= len(blanks):
            for sel in choose_n(letters, len(blanks)):
                chosen_letters = non_blanks + [letters[k] for k in sel]
                words = self.find_words(chosen_letters)
                for word in words:
                    satisfies = len(word) == len(constraint)
                    stats['checked'] += 1
                    if satisfies:
                        for k in range(0, len(word)):
                            if (constraint[k] != ' ') and (constraint[k] != word[k]):
                                satisfies = False
                                break
                    if satisfies:
                        constrained_words.add(word)
        return constrained_words

    def find_all_words(self, letters, target_length=-1, constraint=None, stats={}):
        if len(letters) == 0: return set()
        if stats:
            stats['calls'] += 1
        if (target_length == len(letters)) or target_length == -1:
            words = self.find_words(letters)
            if constraint:
                constrained_words = set()
                for word in words:
                    satisfies = len(word) == len(constraint)
                    stats['checked'] += 1
                    if satisfies:
                        for k in range(0, len(word)):
                            if (constraint[k] != ' ') and (constraint[k] != word[k]):
                                satisfies = False
                                break
                    if satisfies:
                        constrained_words.add(word)
                words = constrained_words
        else:
            words = set()
        if (target_length == -1) or len(letters) > target_length:
            for i in range(len(letters)):
                words = words.union(
                    self.find_all_words(letters[0:i] + letters[(i+1):],
                                        target_length, constraint, stats))
        return words

    def order_by_length(self, words):
        by_length = {}
        for w in words:
            if len(w) not in by_length:
                by_length[len(w)] = set()
            by_length[len(w)].add(w)
        return by_length

if __name__ == '__main__':
    dict_hash = DictHash(sys.argv[1],
                         sys.argv[2],
                         sys.argv[3])
    board = Board(dict_hash, 2)
    no_move = 0
    while not board.done():
        if board.make_auto_play():
            no_move = 0
        else:
            no_move += 1
        if no_move == len(board.players):
            break
        board.print_board()

    board.print_board()
    words = set()
    for i in range(0, 14):
        for j in range(0, 14):
            if board.state[i][j] != ' ':
                for dir in range(0, 2):
                    w = board.trace_word(i, j, dir, board.state[i][j])
                    if len(w) > 1:
                        words.add(w)
    print(words)
    invalid_words = []
    for word in words:
        if not dict_hash.is_word(word):
            invalid_words.append(word)
    if invalid_words:
        print('Invalid words')
        print(invalid_words)
