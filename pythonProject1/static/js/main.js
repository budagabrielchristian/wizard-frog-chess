/* =========================================
   1. SETUP & ASSETS
   ========================================= */

// Preload Images
const frogImages = ['wizard_frog.png', 'frog_thinking.png', 'frog_mad.png', 'frog_happy.png'];
frogImages.forEach(img => { (new Image()).src = '/static/img/' + img; });

// Sound Engine
window.SoundFX = {
    ctx: new (window.AudioContext || window.webkitAudioContext)(),
    playTone: function(freq, type, duration) {
        if (this.ctx.state === 'suspended') this.ctx.resume();
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = type; osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
        gain.gain.setValueAtTime(0.1, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.00001, this.ctx.currentTime + duration);
        osc.connect(gain); gain.connect(this.ctx.destination);
        osc.start(); osc.stop(this.ctx.currentTime + duration);
    },
    move: function() { this.playTone(300, 'triangle', 0.1); },
    capture: function() { this.playTone(150, 'sawtooth', 0.1); setTimeout(() => this.playTone(100, 'sawtooth', 0.1), 50); },
    error: function() { this.playTone(150, 'sawtooth', 0.3); this.playTone(100, 'square', 0.3); },
    success: function() { this.playTone(600, 'sine', 0.1); setTimeout(() => this.playTone(800, 'sine', 0.2), 100); },
    start: function() { this.playTone(200, 'sine', 0.1); setTimeout(() => this.playTone(400, 'sine', 0.2), 100); }
};

/* =========================================
   2. VISUALS (Frog & Zoom)
   ========================================= */
function setFrogMood(mood) {
    const $frogContainer = $('.frog-container');
    const $frogImg = $('.frog-img');
    const basePath = '/static/img/';
    let filename = 'wizard_frog.png';

    $frogContainer.removeClass('frog-thinking frog-mad frog-happy');

    if (mood === 'thinking') { $frogContainer.addClass('frog-thinking'); filename = 'frog_thinking.png'; }
    if (mood === 'mad')      { $frogContainer.addClass('frog-mad'); filename = 'frog_mad.png'; }
    if (mood === 'happy')    { $frogContainer.addClass('frog-happy'); filename = 'frog_happy.png'; }

    $frogImg.attr('src', basePath + filename);

    if (mood !== 'thinking') {
        setTimeout(() => {
            $frogContainer.removeClass('frog-mad frog-happy');
            $frogImg.attr('src', basePath + 'wizard_frog.png');
        }, 2000);
    }
}

// ROBUST CLICK-TO-ZOOM
$(document).on('click', '.analysis-content, #strategyPanel', function() {
    $(this).toggleClass('expanded');
});

/* =========================================
   3. GAME LOGIC
   ========================================= */
var game = new Chess();
var board = null;
var playerColor = 'white'; // Track who the human is playing as

// UI References
var $moveTableBody = $('#moveTable tbody');
var $frogDialogue = $('#frogDialogue');
var $status = $('#statusMessage');
var $reviewControls = $('#reviewControls');
var $moveListPanel = $('#moveListPanel');
var $analysisPanel = $('#analysisPanel');
var $analysisContent = $('#analysisContent');

var isReviewMode = false;
var viewingHistoryIndex = -1;
var reviewMoves = [];

$(document).ready(function() {
    if (window.location.pathname === '/' || window.location.pathname === '/index.html') {
        $.post('/reset', function(res) {
            console.log("Game Synced with Server");
        });
    }
});

var config = {
  draggable: true,
  position: 'start',
  onDragStart: onDragStart,
  onDrop: onDrop,
  onSnapEnd: onSnapEnd,
  pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
  moveSpeed: 'fast',
  snapbackSpeed: 500,
  snapSpeed: 100
};

if (document.getElementById('myBoard')) {
    board = Chessboard('myBoard', config);
}

// Keyboard Controls
$(document).keydown(function(e) {
    if ($(e.target).is('input, textarea')) return;
    if (e.key === "ArrowLeft") { e.preventDefault(); stepHistory(-1); }
    if (e.key === "ArrowRight") { e.preventDefault(); stepHistory(1); }
    if (e.key === "ArrowUp") { e.preventDefault(); jumpToMove(-1); }
    if (e.key === "ArrowDown") { e.preventDefault(); jumpToMove(9999); }
});

// --- FIXED DRAG LOGIC ---
function onDragStart (source, piece) {
  if (isReviewMode) return false;
  if (game.game_over()) return false;

  // Snap back to live game if reviewing
  if (viewingHistoryIndex !== -1 && viewingHistoryIndex < game.history().length - 1) {
      board.position(game.fen());
      viewingHistoryIndex = -1;
      highlightCurrentMove();
  }

  // Only allow moving if it is YOUR turn and YOUR pieces
  if (playerColor === 'white') {
      if (game.turn() === 'b' || piece.search(/^b/) !== -1) return false;
  }
  else if (playerColor === 'black') {
      if (game.turn() === 'w' || piece.search(/^w/) !== -1) return false;
  }

  // CRITICAL FIX: Return true when move is legal
  return true;
}

function onDrop (source, target) {
  var move = game.move({ from: source, to: target, promotion: 'q' });

  if (move === null) {
      SoundFX.error();
      return 'snapback';
  }

  if (move.captured) SoundFX.capture(); else SoundFX.move();

  viewingHistoryIndex = -1;
  updateMoveList();
  sendMoveToServer(move.from + move.to + (move.promotion ? move.promotion : ''));
}

function onSnapEnd () {
    if(viewingHistoryIndex === -1) board.position(game.fen());
}

function sendMoveToServer(uciMove) {
    setFrogMood('thinking');
    $.ajax({
        url: '/move', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ move: uciMove }),
        success: function(res) {
            if(res.error) {
                game.undo(); board.position(game.fen());
                SoundFX.error(); setFrogMood('mad');
                return;
            }

            if (res.engine_move) {
                var m = res.engine_move;
                game.move({ from: m.substring(0,2), to: m.substring(2,4), promotion: m.length>4?m[4]:'q' });
                if(res.message && res.message.includes("capture")) SoundFX.capture(); else SoundFX.move();
            }

            board.position(game.fen());
            updateMoveList();
            setFrogMood('happy');

            if (res.message) $frogDialogue.text(res.message);
            if (res.game_over) {
                $status.html("<b>GAME OVER</b>");
                SoundFX.success();
            }
        }
    });
}

function updateMoveList() {
    $moveTableBody.empty();
    var history = isReviewMode ? reviewMoves : game.history();
    for (var i = 0; i < history.length; i += 2) {
        var whiteMove = history[i];
        var blackMove = history[i+1] || "";
        var row = `<tr>
            <td>${(i/2)+1}.</td>
            <td class="move-cell" id="move-${i}" onclick="window.jumpToMove(${i})">${whiteMove}</td>
            <td class="move-cell" id="move-${i+1}" onclick="window.jumpToMove(${i+1})">${blackMove}</td>
        </tr>`;
        $moveTableBody.append(row);
    }
    if(viewingHistoryIndex === -1 || viewingHistoryIndex >= history.length - 1) {
        $('.move-list-container').scrollTop(9999);
    }
    highlightCurrentMove();
}

function stepHistory(direction) {
    var history = isReviewMode ? reviewMoves : game.history();
    var maxIndex = history.length - 1;
    if (!isReviewMode && viewingHistoryIndex === -1) {
        if (direction === -1) jumpToMove(maxIndex);
        return;
    }
    var newIndex = viewingHistoryIndex + direction;
    if (newIndex < -1) newIndex = -1;
    if (newIndex > maxIndex) newIndex = maxIndex;
    jumpToMove(newIndex);
}

window.jumpToMove = function(index) {
    var history = isReviewMode ? reviewMoves : game.history();
    if (index < -1) index = -1;
    if (index >= history.length) index = history.length - 1;

    viewingHistoryIndex = index;
    var tempGame = new Chess();
    for (var i = 0; i <= index; i++) {
        var moveData = history[i];
        if (typeof moveData === 'string' && moveData.match(/^[a-h][1-8][a-h][1-8][qrbn]?$/)) {
             var moveObj = { from: moveData.substring(0, 2), to: moveData.substring(2, 4), promotion: moveData.length === 5 ? moveData[4] : 'q' };
             tempGame.move(moveObj);
        } else { tempGame.move(moveData); }
    }
    board.position(tempGame.fen());
    SoundFX.move();
    highlightCurrentMove();

    if (index === -1) $('#moveCounter').text("Start");
    else $('#moveCounter').text("Move " + (index + 1));
};

function highlightCurrentMove() {
    $('.move-cell').removeClass('highlight-move');
    if (viewingHistoryIndex !== -1) $(`#move-${viewingHistoryIndex}`).addClass('highlight-move');
}

/* =========================================
   4. HISTORY & ANALYSIS
   ========================================= */
var modal = document.getElementById("historyModal");
$('#historyBtn').click(function() { modal.style.display = "block"; loadHistory(); });
$('.close-modal').click(function() { modal.style.display = "none"; });

function loadHistory() {
    $('#historyListContainer').html("Loading...");
    $.get('/history', function(data) {
        var html = '<ul class="history-list">';
        data.forEach(function(g) {
            var color = g.result === 'win' ? '#d4edda' : (g.result === 'loss' ? '#f8d7da' : '#eee');
            var movesJson = JSON.stringify(g.moves);
            html += `<li style="background:${color}; padding:10px; margin-bottom:5px; border-radius:5px;">
                <strong>${g.date}</strong> - ${g.result.toUpperCase()}<br>
                <div style="margin-top:5px;">
                    <button onclick='startReplay(${movesJson})' class="small-btn">Replay</button>
                    <button onclick='visualAnalyze(${g.id}, ${movesJson})' class="small-btn blue">Deep Analysis</button>
                </div>
            </li>`;
        });
        $('#historyListContainer').html(html+"</ul>");
    });
}

window.visualAnalyze = function(id, moves) {
    startReplay(moves);
    $moveListPanel.hide();
    $analysisPanel.css('display', 'flex');
    $('#analysisContent').html("<em>Summoning the Wizard Frog... (This may take a few seconds)</em>");
    $('#analysisAccuracy').text("--%");
    $('#analysisElo').text("--");
    SoundFX.start(); setFrogMood('thinking');

    $.ajax({
        url: '/analyze_history', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ id: id }),
        success: function(res) {
            setFrogMood('happy'); SoundFX.success();
            if (res.error || typeof res === 'string') { $('#analysisContent').text(res.analysis_text || res); return; }
            if (typeof marked !== 'undefined') { $('#analysisContent').html(marked.parse(res.analysis_text)); } else { $('#analysisContent').text(res.analysis_text); }
            $('#analysisAccuracy').text(res.accuracy + "%");
            $('#analysisElo').text(res.estimated_elo);
            var score = res.accuracy;
            var color = '#d9534f';
            if (score >= 90) color = '#2E8B57'; else if (score >= 70) color = '#DAA520'; else if (score >= 50) color = '#4682B4';
            $('#analysisAccuracy').css('color', color);
        },
        error: function() { setFrogMood('mad'); $('#analysisContent').text("Connection to the Wizard failed."); }
    });
};

window.closeAnalysis = function() { $analysisPanel.hide(); $moveListPanel.show(); };

window.startReplay = function(moves) {
    modal.style.display = "none";
    isReviewMode = true;
    reviewMoves = moves;
    viewingHistoryIndex = -1;
    game.reset(); board.position('start');
    $reviewControls.show();
    $frogDialogue.text("Replay / Analysis Mode");
    updateMoveList();
    $('#moveCounter').text("Start");
};

$('#nextMoveBtn').click(function() { stepHistory(1); });
$('#prevMoveBtn').click(function() { stepHistory(-1); });
$('#exitReviewBtn').click(function() { location.reload(); });

// --- FIXED RESET BUTTON LOGIC ---
$('#resetBtn').click(function() {
    var selectedColor = $('#colorSelect').val();
    playerColor = selectedColor;

    $.ajax({
        url: '/reset',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ color: selectedColor }),
        success: function(res) {
            // Reset the game first
            game.reset();

            // If there's an engine move (playing as Black), apply it
            if (res.engine_move) {
                var m = res.engine_move;
                game.move({ from: m.substring(0,2), to: m.substring(2,4), promotion: m.length>4?m[4]:'q' });
            }

            // Update board and UI
            board.position(game.fen());
            board.orientation(res.orientation);
            $('#statusMessage').text(res.message);
            $('#frogDialogue').text(res.message);
            $('#eloValue').text(res.elo);

            // Update the move list to show the engine's first move
            updateMoveList();
        }
    });
}); // CRITICAL FIX: Added missing closing brace and parenthesis