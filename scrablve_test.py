import unittest
import scrablve


class TestBoard(unittest.TestCase):
    def setUp(self):
        self.dict_hash = scrablve.DictHash('words.txt')

    def testInitialState(self):
        board = scrablve.Board(self.dict_hash, 2)
        self.assertEqual(board.board_as_str(), '\n'.join([' ' * 15] * 15))

    def testScoreWord(self):
        board = scrablve.Board(self.dict_hash, 2)

        self.assertEqual(board.score_word('leppa', check=True), 0)
        self.assertEqual(board.score_word('leppa', check=False), 9)
        self.assertEqual(board.score_word('apple', check=True), 9)

    def testScorePlacedWordInvalid(self):
        board = scrablve.Board(self.dict_hash, 2)
        self.assertEqual(board.score_placed_word(0, 12, 1, 'apple'), (-1, -1))
        self.assertEqual(board.score_placed_word(0, 13, 1, 'apple'), (-1, -1))
        self.assertEqual(board.score_placed_word(12, 0, 0, 'apple'), (-1, -1))
        self.assertEqual(board.score_placed_word(13, 0, 0, 'apple'), (-1, -1))

    def testScorePlacedWord(self):
        board = scrablve.Board(self.dict_hash, 2)
        self.assertEqual(board.score_placed_word(7, 3, 1, 'apple'), (20, True, []))
        self.assertEqual(board.score_placed_word(7, 3, 1, 'lemma'), (20, True, []))
        board.place_word(7, 3, 1, 'apple')

        # Already placed
        self.assertEqual(board.score_placed_word(7, 3, 1, 'lemma'), (-1, -1, []))

        self.assertEqual(board.score_placed_word(2, 3, 0, 'lemm'), (-1, -1, []))
        self.assertEqual(board.score_placed_word(3, 3, 0, 'lemm'), (18, False, []))

    def testTraceWord(self):
        board = scrablve.Board(self.dict_hash, 2)

        board.place_word(7, 3, 1, 'apple')
        self.assertEqual(board.trace_word(7, 8, 1, 's'), 'apples')
        self.assertEqual(board.trace_word(7, 2, 1, 'r'), 'rapple')



if __name__ == '__main__':
    unittest.main()
