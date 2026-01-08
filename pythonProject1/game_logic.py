import warnings

# 1. SILENCE WARNINGS
warnings.simplefilter(action='ignore', category=FutureWarning)

import chess
import chess.engine
import chess.pgn
import json
import os
import random
import datetime
import time
import glob
import io  # <--- CRITICAL IMPORT MOVED TO TOP
import urllib.request
import google.generativeai as genai

# ================= CONFIGURATION =================
# DOUBLE CHECK THESE PATHS MATCH YOUR PC!
STOCKFISH_PATH = r"C:\stockfish\stockfish-windows-x86-64-avx2.exe"
GEMINI_API_KEY = "insert ur own hihi"

DATA_FILE = "player_data.json"
HISTORY_DIR = "history"
HISTORY_JSON = os.path.join(HISTORY_DIR, "matches.json")
OPENINGS_DIR = "openings"
ANALYSIS_DIR = "analysis"

STARTING_ELO = 1000
PLACEMENT_GAMES = 5
K_FACTOR_PLACEMENT = 400  # <--- TURBO BOOST (Win = +200 Elo)
K_FACTOR_NORMAL = 40

print("--- CONNECTING TO WIZARD FROG BRAIN ---")
active_model = None

try:
    genai.configure(api_key=GEMINI_API_KEY)
    preferences = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-1.0-pro']

    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except:
        all_models = []

    candidate_models = []
    for pref in preferences:
        match = next((m for m in all_models if pref in m), None)
        if match: candidate_models.append(match)

    if not candidate_models:
        candidate_models = [m for m in all_models if 'flash' in m.lower()]

    for model_name in candidate_models:
        try:
            print(f"Testing {model_name}...", end=" ")
            test_model = genai.GenerativeModel(model_name)
            test_model.generate_content("test")
            active_model = test_model
            print(f"✅ SUCCESS!")
            break
        except:
            continue

    if not active_model: print("❌ ALL AI MODELS FAILED.")

except Exception as e:
    print(f"❌ CRITICAL ERROR: {e}")


class ChessTrainer:
    def __init__(self):
        self.board = chess.Board()
        self.engine = None
        self.practice_mode = False
        self.target_opening = []
        self.practice_move_index = 0
        self.practice_name = ""
        self.current_opening_data = None

        os.makedirs(HISTORY_DIR, exist_ok=True)
        os.makedirs(OPENINGS_DIR, exist_ok=True)
        os.makedirs(ANALYSIS_DIR, exist_ok=True)

        self._init_history_db()
        self.player_data = self._load_player_data()
        self.game_moves = []
        self._init_engine()

    def _init_history_db(self):
        if not os.path.exists(HISTORY_JSON):
            with open(HISTORY_JSON, 'w') as f: json.dump([], f)

    def _load_player_data(self):
        default_data = {
            "elo": STARTING_ELO,
            "games_played": 0,
            "placement_finished": False,
            "puzzle_elo": 1000,
            "puzzles_solved": 0
        }
        if not os.path.exists(DATA_FILE): return default_data
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                if "puzzle_elo" not in data: data["puzzle_elo"] = 1000
                if "puzzles_solved" not in data: data["puzzles_solved"] = 0
                return data
        except:
            return default_data

    def update_puzzle_rating(self, success):
        is_placement = self.player_data.get("puzzles_solved", 0) < 5
        k_factor = 45 if is_placement else 15

        change = k_factor if success else -10
        self.player_data["puzzle_elo"] += change
        if success: self.player_data["puzzles_solved"] += 1
        self._save_player_data()
        return self.player_data["puzzle_elo"]

    def _save_player_data(self):
        with open(DATA_FILE, 'w') as f: json.dump(self.player_data, f)

    def get_elo(self):
        return self.player_data.get("elo", STARTING_ELO)

    def get_games_played(self):
        return self.player_data.get("games_played", 0)

    def _init_engine(self):
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        except FileNotFoundError:
            print(f"CRITICAL ERROR: Stockfish not found at {STOCKFISH_PATH}")

    def get_available_openings(self):
        files = glob.glob(os.path.join(OPENINGS_DIR, "*.json"))
        openings_list = []
        for filepath in files:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    openings_list.append({
                        "key": os.path.basename(filepath).replace(".json", ""),
                        "name": data.get("name", "Unknown")
                    })
            except:
                pass
        return openings_list

    def add_new_opening_from_ai(self, opening_name):
        try:
            prompt = f"""
            You are a Grandmaster Chess Coach. Create a study for: {opening_name}.
            1. **Strategic Concepts:** Provide 4 distinct concepts.
            2. **Tactical Motifs:** Provide 4 distinct tactics.
            3. **Moves:** Provide the standard main line (approx 8-12 moves) in Standard Algebraic Notation.
            Return strictly valid JSON:
            {{
              "ideas": ["**Control**: ...", "**Battery**: ..."],
              "tactics": ["**Greek Gift**: ...", "**Fork**: ..."],
              "moves": "1. e4 e5 2. Nf3 Nc6..."
            }}
            """
            if not active_model: return {"success": False, "message": "AI is offline."}

            response = active_model.generate_content(prompt)
            content = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)

            # Parse moves to UCI
            pgn_string = data.get("moves", "")
            pgn_io = io.StringIO(pgn_string)
            game = chess.pgn.read_game(pgn_io)

            clean_uci_moves = []
            if game:
                board = game.board()
                for move in game.mainline_moves():
                    clean_uci_moves.append(move.uci())
                    board.push(move)

            data['moves'] = clean_uci_moves
            data['pgn'] = pgn_string
            data['name'] = opening_name

            filename = f"openings/{opening_name.lower().replace(' ', '_')}.json"
            with open(filename, 'w') as f:
                json.dump(data, f)

            return {"success": True, "message": f"I have mastered the {opening_name}!"}
        except Exception as e:
            print(f"Error: {e}")
            return {"success": False, "message": "The magical spirits were confused."}

    def start_practice(self, key):
        filename = key + ".json"
        filepath = os.path.join(OPENINGS_DIR, filename)
        if not os.path.exists(filepath): return "Ribbit? I can't find that scroll."

        with open(filepath, 'r') as f: self.current_opening_data = json.load(f)

        self.board.reset()
        self.game_moves = []
        self.practice_mode = True

        raw_moves = self.current_opening_data.get("moves", [])
        self.target_opening = raw_moves.split() if isinstance(raw_moves, str) else raw_moves
        self.practice_name = self.current_opening_data.get("name", "Unknown Opening")
        self.practice_move_index = 0

        return {
            "message": f"Let's learn the {self.practice_name}!",
            "ideas": self.current_opening_data.get("ideas", []),
            "tactics": self.current_opening_data.get("tactics", []),
            "pgn": self.current_opening_data.get("pgn", "Moves not available.")
        }

    def reset_game(self, player_color="white"):
        self.board.reset()
        self.game_moves = []
        self.practice_mode = False

        if player_color == "black":
            self._configure_difficulty()
            res = self.engine.play(self.board, chess.engine.Limit(time=0.1))
            self.board.push(res.move)
            self.game_moves.append(res.move)
            return {
                "fen": self.board.fen(),
                "message": "Ribbit! I have made the first move.",
                "elo": self.get_elo(),
                "orientation": "black",
                "engine_move": res.move.uci()  # ADD THIS LINE
            }

        return {
            "fen": self.board.fen(),
            "message": "Ribbit! You command the White pieces.",
            "elo": self.get_elo(),
            "orientation": "white"
        }

    def make_player_move(self, uci_move):
        if self.practice_mode: return self._handle_practice_move(uci_move)
        try:
            move = chess.Move.from_uci(uci_move)
        except:
            return {"error": "Invalid Move"}

        if move in self.board.legal_moves:
            self.board.push(move)
            self.game_moves.append(move)
            if self.check_game_over(chess.WHITE): return self._get_game_over_response(chess.WHITE)
            return self.make_engine_move()
        return {"error": "Illegal move"}

    def get_puzzle(self):
        classic_puzzles = [
            {"fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
             "solution": ["f3e5", "d7d6"],
             "hint": "A classic opening trap!", "theme": "Fork", "user_puzzle_elo": 1000},
            {"fen": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR b KQkq - 3 3",
             "solution": ["d8e7"],
             "hint": "Defend f7!", "theme": "Opening Defense", "user_puzzle_elo": 1000}
        ]
        try:
            print("🐸 Wizard is scrying Lichess.org...")
            with urllib.request.urlopen("https://lichess.org/api/puzzle/daily") as url:
                data = json.loads(url.read().decode())

                pgn_text = data["game"]["pgn"]
                target_ply = data["puzzle"]["initialPly"]

                pgn_io = io.StringIO(pgn_text)
                game = chess.pgn.read_game(pgn_io)
                board = game.board()

                for move in game.mainline_moves():
                    if board.ply() >= target_ply: break
                    board.push(move)

                # FIX: Lichess solution includes the "blunder" move first
                # We need to remove it since the puzzle position is AFTER that move
                solution = data["puzzle"]["solution"]

                # The first move in the solution is the opponent's blunder that created the puzzle
                # Apply it to get to the actual puzzle starting position
                if solution and len(solution) > 0:
                    blunder_move = chess.Move.from_uci(solution[0])
                    board.push(blunder_move)
                    solution = solution[1:]  # Remove the blunder from the solution

                return {
                    "fen": board.fen(),
                    "solution": solution,  # Now starts with YOUR first move
                    "hint": f"Rating: {data['puzzle']['rating']} | Theme: {data['puzzle']['themes'][0]}",
                    "theme": "Daily Puzzle",
                    "user_puzzle_elo": self.player_data.get("puzzle_elo", 1000)
                }
        except Exception as e:
            print(f"Lichess Scrying Failed: {e}")
            return random.choice(classic_puzzles)

    def _handle_practice_move(self, uci_move):
        if not self.target_opening or self.practice_move_index >= len(self.target_opening):
            self.practice_mode = False
            return {"message": "Practice finished."}

        correct_uci = self.target_opening[self.practice_move_index]
        if uci_move != correct_uci:
            correct_move_obj = chess.Move.from_uci(correct_uci)
            readable_move = self.board.san(correct_move_obj)
            return {"error": "Practice Error", "message": f"Try playing {readable_move}!"}

        self.board.push(chess.Move.from_uci(uci_move))
        self.game_moves.append(chess.Move.from_uci(uci_move))
        self.practice_move_index += 1

        if self.practice_move_index >= len(self.target_opening):
            self.practice_mode = False
            return {"fen": self.board.fen(), "message": "Mastered!", "practice_complete": True}

        eng_move_uci = self.target_opening[self.practice_move_index]
        self.board.push(chess.Move.from_uci(eng_move_uci))
        self.game_moves.append(chess.Move.from_uci(eng_move_uci))
        self.practice_move_index += 1

        if self.practice_move_index >= len(self.target_opening):
            self.practice_mode = False
            return {"engine_move": eng_move_uci, "fen": self.board.fen(), "message": "Opening complete. Fight!"}

        return {"engine_move": eng_move_uci, "fen": self.board.fen(), "message": "Correct."}

    def make_engine_move(self):
        self._configure_difficulty()
        try:
            res = self.engine.play(self.board, chess.engine.Limit(time=0.1))
            self.board.push(res.move)
            self.game_moves.append(res.move)
            if self.check_game_over(chess.BLACK): return self._get_game_over_response(chess.BLACK)
            return {"engine_move": res.move.uci(), "fen": self.board.fen(),
                    "message": self.get_frog_message("continue")}
        except:
            return {"error": "Engine failed"}

    def _get_game_over_response(self, winner):
        win = (winner == chess.WHITE)
        self._update_elo(win)
        res_code = "win" if win else "loss"
        narrative = self._end_game_processing(res_code)
        return {"game_over": True, "message": self.get_frog_message(res_code), "narrative": narrative,
                "fen": self.board.fen()}

    def check_game_over(self, color):
        if self.board.is_checkmate(): return True
        if self.board.is_stalemate(): return True
        if self.board.is_insufficient_material(): return True
        return False

    def _configure_difficulty(self):
        skill = 2
        if self.player_data.get("placement_finished"):
            skill = max(0, min(20, int((self.get_elo() - 1000) / 120)))
        try:
            self.engine.configure({"Skill Level": skill})
        except:
            pass

    def analyze_specific_game(self, game_id):
        filename = f"analysis_{game_id}.json"
        filepath = os.path.join(ANALYSIS_DIR, filename)

        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                pass

        history = self.get_match_history()
        g = next((x for x in history if x["id"] == int(game_id)), None)

        if not g: return {"analysis_text": "Game not found.", "accuracy": 0, "estimated_elo": 0}
        if not active_model: return {"analysis_text": "AI Offline.", "accuracy": 0, "estimated_elo": 0}

        moves = g.get('moves', [])
        pgn = ' '.join(moves) if moves else "No moves"

        prompt = f"""
        Act as a Grandmaster Chess Coach with a Wizard Frog persona.
        Analyze this chess game played by the user. Moves: {pgn}. Result: {g['result']}
        Structure your analysis in Markdown.
        Return strictly valid JSON:
        {{
            "analysis_text": "## 🧙‍♂️ The Wizard's Scroll\\n\\n[Analysis content]",
            "accuracy": 85,
            "estimated_elo": 1250
        }}
        """
        try:
            response = active_model.generate_content(prompt)
            content = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)
            with open(filepath, 'w') as f:
                json.dump(data, f)
            return data
        except Exception as e:
            return {"analysis_text": f"The Wizard is confused: {e}", "accuracy": 0, "estimated_elo": 0}

    def _end_game_processing(self, res):
        narrative = "Good game."
        if active_model:
            try:
                narrative = active_model.generate_content(
                    f"Frog recap. Result {res}. Moves {' '.join([m.uci() for m in self.game_moves])}").text.strip()
            except:
                pass
        self._save_game_to_history(res, narrative)
        return narrative

    def _update_elo(self, win):
        k = K_FACTOR_PLACEMENT if self.player_data["games_played"] < PLACEMENT_GAMES else K_FACTOR_NORMAL
        if self.player_data["games_played"] >= PLACEMENT_GAMES: self.player_data["placement_finished"] = True
        change = k * ((1.0 if win else 0.0) - 0.5)
        self.player_data["elo"] = max(100, int(self.player_data["elo"] + change))
        self.player_data["games_played"] += 1
        self._save_player_data()

    def _save_game_to_history(self, res, narr):
        h = self.get_match_history()
        h.insert(0, {"id": int(time.time()), "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "result": res,
                     "moves": [m.uci() for m in self.game_moves], "narrative": narr, "elo": self.player_data["elo"]})
        with open(HISTORY_JSON, 'w') as f: json.dump(h, f)

    def get_match_history(self):
        if os.path.exists(HISTORY_JSON):
            with open(HISTORY_JSON, 'r') as f: return json.load(f)
        return []

    def get_frog_message(self, ctx):
        return random.choice(["Ribbit!", "Croak!", "Hmm...", "Don't eat the fly!"])

    def __del__(self):
        if self.engine: self.engine.quit()


trainer = ChessTrainer()