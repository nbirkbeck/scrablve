import os
import sys
import enum
import random

# Letter frequency
_FREQ = [9, 2, 2, 4, 12,
         2, 3, 2, 9, 1,
         1, 4, 2, 6, 8,
         2, 1, 6, 4, 6,
         4, 2, 2, 1, 2, 1]
_LETTER_SCORE = [13 - f for f in _FREQ] # TODO!!!
print(_LETTER_SCORE)

Multiplier = enum.Enum('Multiplier',
                            names=[
                                'NONE',
                                'DOUBLE_LETTER',
                                'TRIPLE_LETTER',
                                'DOUBLE_WORD',
                                'TRIPLE_WORD'])

# Board has tripple word every 7 (except for center)
class Board:
    def __init__(self, dict_hash, num_players):
        board = []
        for i in range(0, 15):
            row = [Multiplier.NONE for i in range(0, 15)]
            board.append(row)

        state = []
        for i in range(0, 15):
            row = [' ' for i in range(0, 15)]
            state.append(row)

        # Diagonals are double word
        for i in range(0, 14):
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

    def print_board(self):
        print('\n'.join([''.join(row) for row in self.state]))

    def score_word(self, word):
        if not self.dict_hash.is_word(word):
            return 0
        score = 0
        for letter in word:
            score += _LETTER_SCORE[ord(letter) - ord('a')]
        return score

    def score_placed_word(self, i, j, direction, word):
        if not self.dict_hash.is_word(word):
            return -1, -1

        # Check for valid positions first
        pos = [i, j]
        for k in range(len(word)):
            if max(pos[0], pos[1]) >= 15:
                return -1
            s = self.state[pos[0]][pos[1]]
            if (s != ' ') and (s != word[k]):
                return -1, -1
            pos[direction] += 1

        pos = [i, j]
        end_pos = [i, j]
        end_pos[direction] += (len(word) - 1)
        word_mult = 1

        # Need to check for adding a prefix/suffix to an existing word
        prefix = self.trace_word(pos[0], pos[1], direction, word[0])
        prefix = prefix[:-1]

        suffix = self.trace_word(end_pos[0], end_pos[1],
                                 direction, word[-1])
        suffix = suffix[1:]

        if not self.dict_hash.is_word(prefix + word + suffix):
            return -1, -1

        pre_score = self.score_word(prefix) + self.score_word(suffix)
        score = pre_score
        for k in range(len(word)):
            letter = word[k]
            letter_score = _LETTER_SCORE[ord(letter) - ord('a')]
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
                #if len(letters):
                #    print('letters: %s' % letters)
                if len(letters) > 1:
                #    print('Word:', letters)
                    if not self.dict_hash.is_word(letters):
                        return -1, -1
                    other_words_score += self.score_word(letters)
                    num_other_words += 1
            pos[direction] += 1

        valid = (other_words_score + pre_score) > 0 and num_other_words <= 2
        return word_score + other_words_score, valid

    def trace_word(self, i, j, direction, letter):
        pos = [i, j]
        if pos[direction] > 0:
            pos[direction] -= 1
        while pos[direction] >= 0 and self.state[pos[0]][pos[1]] != ' ':
            pos[direction] -= 1
        if (pos[direction] < 0) or (self.state[pos[0]][pos[1]] == ' '):
            pos[direction] += 1
        start = pos[direction]

        pos = [i, j]
        if pos[direction] < 14:
            pos[direction] += 1
        while pos[direction] < 15 and self.state[pos[0]][pos[1]] != ' ':
            pos[direction] += 1
        if (pos[direction] >= 15) or (self.state[pos[0]][pos[1]] == ' '):
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
        return ''.join(w)


    def get_candidate_positions(self, letters):
        words = self.dict_hash.find_all_words(letters)
        max_word = ''
        max_score = -1
        pos = []
        dir = 0

        if self.num_played == 0:
            col = 7
            for w in words:
                for row in range(7 - len(w) + 1, 8):
                    score, _ = self.score_placed_word(row, col, dir, w)
                    if score > max_score:
                        max_score = score
                        pos = [row, col]
                        max_word = w
        else:
            # Try to use our own letters only
            for w in words:
                for row in range(0, 15):
                    for col in range(0, 15 - len(w) + 1):
                        score, valid = self.score_placed_word(row, col, 1, w)
                        break
                        if valid and (score > max_score):
                            print(w, score, valid)
                            max_score = score
                            pos = [row, col]
                            max_word = w
                            dir = 1
                for row in range(0, 15 - len(w) + 1):
                    for col in range(0, 15):
                        score, valid = self.score_placed_word(row, col, 0, w)
                        break
                        if valid and (score > max_score):
                            print(w, score, valid)
                            max_score = score
                            pos = [row, col]
                            max_word = w
                            dir = 0

            # Try to make words with existing letters
            for d in range((self.num_played % 2), 2):
                for row in range(0, 15):
                    for col in range(0, 15):
                        #print(row, col)
                        subset = [' ' for i in range(0, 15)]
                        p = [row, col]
                        for n in range(0, 15):
                            subset[n] = self.state[p[0]][p[1]]
                            p[d] += 1
                            if p[d] >= 15:
                                break

                        for n in range(5, len(subset)):
                            cons = subset[0:n]
                            extra_letters = []
                            for c in cons:
                                if c != ' ':
                                    extra_letters.append(c)
                            if not extra_letters: continue
                            words = self.dict_hash.find_all_words(letters + extra_letters,
                                                                  len(cons), cons)
                            for w in words:
                                score, _ = self.score_placed_word(row, col, d, w)
                                print('new:', row, col, d, w, score, max_score, '[' + ''.join(cons) + ']')
                                if score > max_score:
                                    max_score = score
                                    pos = [row, col]
                                    max_word = w
                                    dir = d
                                    print('new found')


        print(max_score, max_word, pos)
        return max_score, max_word, pos, dir

    def draw_letters(self, n):
        num_letters = 0
        all_letters = []
        for i in range(len(self.letters)):
            num_letters += self.letters[i]
            all_letters += [chr(i + ord('a')) for _ in range(self.letters[i])]

        random.shuffle(all_letters)
        chosen = all_letters[0:n]
        remaining = all_letters[n:]
        self.letters = [0] * 26
        for l in remaining:
            self.letters[ord(l) - ord('a')] += 1
        return chosen


    def make_play(self):
        pi = self.num_played % len(self.players)
        print(self.players[pi].letters)
        max_score, max_word, pos, dir = self.get_candidate_positions(
            self.players[pi].letters)
        print(max_score, max_word, pos, dir)
        if max_score > 0:
            hist = {}
            for l in self.players[pi].letters:
                if l not in hist:
                    hist[l] = 0
                hist[l] += 1
            for k in range(len(max_word)):
                if self.state[pos[0]][pos[1]] == ' ':
                    hist[max_word[k]] -= 1
                    self.state[pos[0]][pos[1]] = max_word[k]
                pos[dir] += 1
            letters = []
            for h in hist:
                letters += [h] * hist[h]
            self.players[pi].letters = (letters +
                                        self.draw_letters(len(max_word)))
            self.players[pi].score += max_score
            print(self.players[pi].letters)
        self.num_played += 1
        print([self.players[i].score for i in range(len(self.players))])

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
    def __init__(self, filename):
        with open(filename, 'r') as f:
            words = [w.strip() for w in f.readlines()]

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

    def find_all_words(self, letters, target_length=-1, constraint=None):
        if len(letters) == 0: return set()
        if (target_length == len(letters)) or target_length == -1:
            words = self.find_words(letters)
            if constraint:
                constrained_words = set()
                for word in words:
                    satisfies = len(word) == len(constraint)
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
                                        target_length, constraint))
        return words

    def order_by_length(self, words):
        by_length = {}
        for w in words:
            if len(w) not in by_length:
                by_length[len(w)] = set()
            by_length[len(w)].add(w)
        return by_length

if __name__ == '__main__':
    dict_hash = DictHash(sys.argv[1])
    board = Board(dict_hash, 2)
    while not board.done():
        board.make_play()
        board.print_board()
