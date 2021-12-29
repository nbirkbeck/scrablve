class Client extends EventTarget {
  constructor(gameId, playerId) {
    super();

    this.gameId = gameId;
    this.playerId = playerId;
    this.url = "";
    this.letters = [];
    this.availableLetters = [];
    this.ready = false;
    this.currentPlayer = -1;
    this.numPlayed = 0;
    this.board = [];
    this.candidatePositions = [];
    for (var i = 0; i < 15; i++) {
      var row = [];
      for (var j = 0; j < 15; ++j) {
        row.push(' ');
      }
      this.board.push(row);
    }
    this.logs = []
  }

  fireEvent_(event_type, detail) {
    this.dispatchEvent(new CustomEvent(event_type, {
      "detail": detail
    }));
  }

  fireLettersChanged() {
    this.fireEvent_(Events.LETTERS_CHANGED, {
      "letters": this.letters,
      "availableLetters": this.availableLetters,
    });
  }

  fireLetterPlaced(i, j, letter) {
    this.fireEvent_(Events.LETTER_PLACED, {
      "i": i,
      "j": j,
      "letter": letter,
    });
  }

  fireBoardChanged() {
    this.fireEvent_(Events.BOARD_CHANGED, {
      "board": this.board,
    });
  }

  fireLogsChanged() {
    this.fireEvent_(Events.LOGS_CHANGED, {
      "logs": this.logs,
    });
  }
  
  fireCandidatesChanged() {
    this.fireEvent_(Events.CANDIDATES_CHANGED, {
      "candidates": this.candidatePositions,
    });
  }

  fireStatus() {
    this.fireEvent_(Events.STATUS, {});
  }
};

Client.prototype.sendStatus = function() {
  $.ajax({
    "type": "POST",
    "url": `${this.url}/api/send_status`,
    "data": JSON.stringify({
      "game_id": this.gameId,
      "player_id": this.playerId,
      "num_played": this.numPlayed,
    }),
    "dataType": "json",
  }).done((x) => {
    this.ready = x.ready;
    this.currentPlayer = x.current_player;
    if ("board_state" in x) {
      this.setBoardState(x.board_state);
    }
    if ("logs" in x) {
      for (var i in x.logs) {
        this.logs.push(x.logs[i]);
      }
      this.fireLogsChanged();
    }
    this.scores = x.scores;
    if ("num_played" in x) {
      this.numPlayed = x.num_played;
      console.log(this.numPlayed);
    }
    this.fireStatus();
  });
};

Client.prototype.joinGame = function() {
  $.ajax({
    "type": "POST",
    "url": `${this.url}/api/join_game`,
    "data": JSON.stringify({
      "game_id": this.gameId,
      "player_id": this.playerId,
    }),
    "dataType": "json",
  }).done((x) => {
    this.setLetters(x.letters);
  });
};

Client.prototype.getCandidatePositions = function() {
  $.ajax({
    "type": "POST",
    "url": `${this.url}/api/get_candidate_positions`,
    "data": JSON.stringify({
      "game_id": this.gameId,
      "player_id": this.playerId,
    }),
    "dataType": "json",
  }).done((x) => {
    var i = 0;
    this.candidatePositions = [];
    for (var i in x.positions) {
      this.candidatePositions.push(x.positions[i]);
    }
    this.fireCandidatesChanged();
  });
};

Client.prototype.checkValid = function(callback) {
  var valid = client.isCurrentMoveValid();
  if (!valid) {
    console.log('Word is not valid');
    return;
  }
  $.ajax({
    "type": "POST",
    "url": `${this.url}/api/score_placed_word`,
    "data": JSON.stringify({
      "game_id": this.gameId,
      "move": {
        "i": valid[0][0],
        "j": valid[0][1],
        "direction": valid[1],
        "word": valid[2],
      }
    }),
    "dataType": "json",
  }).done((x) => {
    callback(x.status == "OK", x.score, x.details);
  });
};

Client.prototype.makePlay = function() {
  var valid = client.isCurrentMoveValid();
  if (!valid) {
    console.log('Not valid');
    return;
  }
  $.ajax({
    "type": "POST",
    "url": `${this.url}/api/move`,
    "data": JSON.stringify({
      "game_id": this.gameId,
      "player_id": this.playerId,
      "move": {
        "i": valid[0][0],
        "j": valid[0][1],
        "direction": valid[1],
        "word": valid[2],
      }
    }),
    "dataType": "json",
  }).done((x) => {
    // TODO: check validity
    console.log('Made move response');
    console.log(x);
    if ("letters" in x) {
      this.setLetters(x.letters);
    }
    this.scores = x.scores;
    this.currentPlayer = x.current_player;
    if ("board_state" in x) {
      this.setBoardState(x.board_state);
    }
    this.fireStatus();
  });
};

Client.prototype.placeLetter = function(i, j, letter) {
  console.log('place letter:', i, j, letter);
  var changed = false;
  var return_value = false;
  for (var k in this.letters) {
    if (this.availableLetters[k].length > 0 &&
        this.availableLetters[k][0] == i &&
        this.availableLetters[k][1] == j) {
      this.availableLetters[k] = [];
      this.fireLetterPlaced(i, j, '');
      changed = true;
      break;
    }
  }

  for (var k in this.letters) {
    if (this.availableLetters[k].length > 0) continue;
    if (this.letters[k] == letter) {
      this.availableLetters[k] = [i, j];
      changed = true;
      return_value = true;
      this.fireLetterPlaced(i, j, letter);
      break;
    }
  }
  if (changed) {
    this.fireLettersChanged();
  }
  return return_value;
};

Client.prototype.isCurrentMoveValid = function() {
  var minPos = [15, 15];
  var maxPos = [0, 0];
  var placed = {};
  for (var i in this.letters) {
    if (this.availableLetters[i].length > 0) {
      var pos = this.availableLetters[i];
      minPos[0] = Math.min(minPos[0], pos[0]);
      minPos[1] = Math.min(minPos[1], pos[1]);
      maxPos[0] = Math.max(maxPos[0], pos[0]);
      maxPos[1] = Math.max(maxPos[1], pos[1]);
      if (!placed.hasOwnProperty(pos[0])) {
        placed[pos[0]] = {};
      }
      placed[pos[0]][pos[1]] = this.letters[i];
    }
  }
  var size = [
    maxPos[0] - minPos[0],
    maxPos[1] - minPos[1]
  ];
  if (!(size[0] == 0 || size[1] == 0)) return null;

  if (size[0] > 0) dir = 0;
  else dir = 1;
  var pos = [minPos[0], minPos[1]];
  var word = '';
  while (pos[dir] <= maxPos[dir]) {
    if (placed.hasOwnProperty(pos[0]) &&
        placed[pos[0]].hasOwnProperty(pos[1])) {
      word += placed[pos[0]][pos[1]];
    } else {
      word += this.board[pos[0]][pos[1]];
    }
    pos[dir] += 1;
  }
  if (word.indexOf(' ') >= 0) return null;

  return [minPos, dir, word];
};

Client.prototype.setBoardState = function(state) {
  var rows = state.split('\n');
  for (var i in rows) {
    for (var j = 0; j < 15; ++j) {
      this.board[i][j] = rows[i][j];
    }
  }
  console.log('board state');
  console.log(state);
  this.fireBoardChanged();
};

Client.prototype.setLetters = function(letters) {
  this.availableLetters = [];
  for (var i in letters) {
    this.availableLetters.push([]);
  }
  this.letters = letters.map((x) => x[0]);
  this.candidatePositions = [];

  this.fireLettersChanged();
  this.fireCandidatesChanged();
};

Client.prototype.placeCandidate = function(i) {
  // Clear placement.
  var cand = this.candidatePositions[i];
  console.log('Placing candidate', i, cand);
  for (var k in this.letters) {
    if (this.availableLetters[k].length > 0) {
      var i = this.availableLetters[k][0];
      var j = this.availableLetters[k][1];
      this.availableLetters[k] = [];
      this.fireLetterPlaced(i, j, '');
    }
  }

  var pos = [cand[1], cand[2]];
  var dir = cand[3];
  var word = cand[4];
  for (var k in word) {
    if (this.board[pos[0]][pos[1]] == ' ') {
      this.placeLetter(pos[0], pos[1], word[k]);
    }
    pos[dir]++;
  }
  this.fireLettersChanged();
};
