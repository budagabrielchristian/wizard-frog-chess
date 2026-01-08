from flask import Flask, render_template, jsonify, request
from game_logic import trainer

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html', elo=trainer.get_elo(), games=trainer.get_games_played())


@app.route('/openings_hall')
def openings_hall():
    return render_template('openings.html')


@app.route('/move', methods=['POST'])
def move():
    data = request.json
    result = trainer.make_player_move(data.get('move'))
    result['current_elo'] = trainer.get_elo()
    return jsonify(result)


@app.route('/get_openings', methods=['GET'])
def get_openings():
    return jsonify(trainer.get_available_openings())


@app.route('/start_opening', methods=['POST'])
def start_opening():
    opening_key = request.json.get('opening')
    response_data = trainer.start_practice(opening_key)
    if isinstance(response_data, str):
        return jsonify({"message": response_data})

    return jsonify({
        "message": response_data["message"],
        "ideas": response_data["ideas"],
        "tactics": response_data["tactics"],
        "fen": trainer.board.fen()
    })


@app.route('/add_opening', methods=['POST'])
def add_opening():
    name = request.json.get('name')
    result = trainer.add_new_opening_from_ai(name)
    return jsonify(result)


@app.route('/analyze_history', methods=['POST'])
def analyze_history():
    game_id = request.json.get('id')
    # This now returns a DICTIONARY (text, accuracy, elo), not just a string
    result = trainer.analyze_specific_game(game_id)
    return jsonify(result)


@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(trainer.get_match_history())

# --- ADD THESE NEW ROUTES ---
@app.route('/puzzles_hall')
def puzzles_hall():
    return render_template('puzzles.html')

@app.route('/get_puzzle', methods=['GET'])
def get_puzzle():
    result = trainer.get_puzzle()
    return jsonify(result)

@app.route('/puzzle_success', methods=['POST'])
def puzzle_success():
    new_rating = trainer.update_puzzle_rating(True)
    return jsonify({"new_elo": new_rating})

@app.route('/puzzle_fail', methods=['POST'])
def puzzle_fail():
    new_rating = trainer.update_puzzle_rating(False)
    return jsonify({"new_elo": new_rating})


@app.route('/reset', methods=['POST'])
def reset():
    # Get color from the button click (default to white if missing)
    data = request.get_json() or {}
    color = data.get('color', 'white')

    # Pass color to the trainer
    response = trainer.reset_game(color)

    return jsonify(response)


if __name__ == '__main__':
    # use_reloader=False means you MUST manually restart the script if you change code!
    app.run(debug=True, port=5000, use_reloader=False)