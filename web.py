import enum
import collections
import json
import os
import signal
import pickle
import sys
import time
import scrabble
from http.server import HTTPServer, SimpleHTTPRequestHandler

API_HANDLERS = {
    'create_game': lambda x, y: x.api_create_game(y),
    'join_game': lambda x, y: x.api_join_game(y),
    'send_status': lambda x, y: x.api_send_status(y),
    'move': lambda x, y: x.api_move(y),
    'score_placed_word': lambda x, y: x.api_score_placed_word(y),
    'get_candidate_positions': lambda x, y: x.api_get_candidate_positions(y),
}

class Status:
    OK ='OK'
    INVALID_ARGUMENT = 'INVALID_ARGUMENT'
    INVALID_MOVE = 'INVALID_MOVE'
    UNKOWN_GAME = 'UNKOWN_GAME'
    UNKOWN_PLAYER = 'UNKOWN_PLAYER'


dict_hash = scrabble.DictHash("words.txt", "words.2.txt", "words.3.txt")

class Game(object):
    def __init__(self, game_id, num_players):
        self.game_id = game_id
        self.num_players = num_players
        self.last_seen = [0] * num_players
        self.current_player = 0
        self.board = scrabble.Board(dict_hash, num_players)
        self.log = []

    def update_status(self, player_id):
        self.last_seen[player_id] = time.time()

    def ready(self):
        for last_seen in self.last_seen:
            if (time.time() - last_seen) > 30: return False
        return True

games = {}

def save_games():
    pickle.dump(games, open('games/games.pkl', 'wb'))


def restore_games():
    if os.path.exists('games/games.pkl'):
        games = pickle.load(open('games/games.pkl', 'rb'))
        print('Loaded %d games' % len(games))
        return games
    return {}


def ctrl_c_handler(sig, frame):
    print('Ctrl+C pressed! Saving games...')
    save_games()
    sys.exit(0)


def get_game_id(request):
    if "game_id" not in request:
        return None, {
            "status": Status.INVALID_ARGUMENT,
        }
    if request["game_id"] not in games:
        return None, {
            "status": Status.UNKOWN_GAME,
        }
    return request["game_id"], None

def get_player_id(request, game):
    if "player_id" not in request:
        return None, {
            "status": Status.INVALID_ARGUMENT,
        }
    if (request["player_id"] < 0) or (request["player_id"] >= game.num_players):
        return None, {
            "status": Status.UNKOWN_PLAYER,
        }
    return request["player_id"], None


class GameHandler(SimpleHTTPRequestHandler):
    def redirect(self, url):
        self.send_response(302)
        self.send_header('Location', url)
        self.end_headers()

    def api_create_game(self, request):
        num_players = 2
        if "num_players" in request:
            num_players = request["num_players"]
        if (num_players > 4) or (num_players <= 1):
            return {"status": Status.INVALID_ARGUMENT}

        game_id = len(games)
        games[game_id] = Game(game_id, num_players)
        return {
            "status": Status.OK,
            "game_id": game_id,
        }

    def api_join_game(self, request):
        game_id, response = get_game_id(request)
        if game_id is None: return response

        game = games[game_id]
        player_id, response = get_player_id(request, game)
        print("player_id", player_id)
        if player_id is None: return response

        return {
            "status": Status.OK,
            "letters": game.board.players[player_id].letters
        }

    def api_send_status(self, request):
        game_id, response = get_game_id(request)
        if game_id is None: return response

        game = games[game_id]
        player_id, response = get_player_id(request, game)
        if player_id is None: return response

        board_update = {}

        game.update_status(player_id)
        response = {
            "status": Status.OK,
            "ready": game.ready(),
            "current_player": game.current_player,
            "scores": [player.score for player in game.board.players],
        }
        if "num_played" in request:
            if game.board.num_played != request["num_played"]:
                response["num_played"] = game.board.num_played
                response["board_state"] = game.board.state_as_str()
                response["logs"] = game.log[max(request["num_played"], 0):]
        return response

    def api_move(self, request):
        game_id, response = get_game_id(request)
        if game_id is None: return response

        game = games[game_id]
        player_id, response = get_player_id(request, game)
        if player_id is None: return response

        if game.current_player != player_id:
            return {
                "status": Status.INVALID_ARGUMENT
            }

        move = request["move"]
        pos = [move["i"], move["j"]]
        word = move["word"]
        direction = move["direction"]
        score, valid, _ = game.board.score_placed_word(pos[0], pos[1], direction, word)

        status = Status.INVALID_MOVE
        move_info = []
        if valid or game.board.num_played == 0:
            status = Status.OK
            num_played = game.board.num_played
            game.board.make_play(player_id, pos, direction, word, score)
            scores = [player.score for player in game.board.players]
            game.log.append("[%d] Player %d earned %d with word=%s (%s)" % (
                game.board.num_played, player_id, score, word, scores))
            game.current_player = (game.current_player + 1) % game.num_players

        return {
            "status": status,
            "ready": game.ready(),
            "current_player": game.current_player,
            "scores": [player.score for player in game.board.players],
            "letters": game.board.players[player_id].letters,
            "move_info": move_info,
            "board_state": game.board.state_as_str(),
        }

    def api_score_placed_word(self, request):
        game_id, response = get_game_id(request)
        if game_id is None: return response
        game = games[game_id]
        
        move = request["move"]
        pos = [move["i"], move["j"]]
        word = move["word"]
        direction = move["direction"]
        score, valid, details = game.board.score_placed_word(pos[0], pos[1], direction, word, info=True)

        status = Status.OK if valid else Status.INVALID_MOVE
        return {
            "status": status,
            "score": score,
            "details": details,
        }

    def api_get_candidate_positions(self, request):
        game_id, response = get_game_id(request)
        if game_id is None: return response
        game = games[game_id]

        player_id, response = get_player_id(request, game)
        if player_id is None: return response

        positions = game.board.get_candidate_positions(game.board.players[player_id].letters, 10)

        status = Status.OK
        return {
            "status": status,
            "positions": positions,
        }
    
    def do_POST(self):
        if self.path.startswith('/api'):
            method = self.path.lstrip('/api/')
            if method in API_HANDLERS:
                length = int(self.headers['Content-Length'])
                if length > 0:
                    data = self.rfile.read(length).decode("utf-8")
                    data = json.loads(data)
                else:
                    data = {}
                response = API_HANDLERS[method](self, data)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(json.dumps(response), "utf8"))

    def do_GET(self):
        if self.path.startswith('/api'):
            method = self.path.lstrip('/api/')
            if method in API_HANDLERS:
                response = API_HANDLERS[method](self, {})
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(json.dumps(response), "utf8"))

        elif self.path.startswith('/static'):
            return SimpleHTTPRequestHandler.do_GET(self)
        elif self.path == '/':
            return self.redirect('/static/index.html')
        else:
            return self.send_error(500, 'Internal error')


if __name__ == '__main__':
    signal.signal(signal.SIGINT, ctrl_c_handler)
    games = restore_games()

    address = 'localhost'
    if len(sys.argv) > 1:
        address = '192.168.1.16'
    httpd = HTTPServer((address, 8000), GameHandler)
    httpd.serve_forever()
