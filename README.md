# Wizard Frog Chess

Wizard Frog Chess is an interactive, AI-powered chess web application. Built with a Python Flask backend and integrated with Google Generative AI, it provides a comprehensive platform for chess enthusiasts to play, learn, and analyze their games. The application features a unique learning environment guided by a "Wizard Frog" persona, offering real-time gameplay, tactical puzzles, and in-depth post-match analysis.

## Description

The goal of Wizard Frog Chess is to provide an all-in-one chess learning experience. Rather than just playing against a standard engine, users can practice specific openings, solve dynamically rated puzzles, and receive detailed AI feedback on their matches. The integration of modern web technologies with a robust Python chess backend ensures a smooth and responsive experience for players of all skill levels.

## Features

* **Interactive Gameplay**: Play standard chess matches as either White or Black against the backend system.
* **AI-Powered Analysis**: Leverage Google Generative AI to generate detailed post-match reports, complete with accuracy calculations and performance ELO metrics.
* **Opening Dojo**: Practice established chess openings or dynamically generate and learn new opening sequences using AI.
* **Puzzle Tower**: Test your tactical skills with a built-in puzzle system that dynamically updates your rating based on success or failure.
* **Match Archives & Replay Mode**: Browse your historical match data and step through past games move-by-move using the interactive replay controls.
* **Player Statistics**: Track your overall ELO rating and progress directly from the dashboard.

## Technologies Used

* **Backend Framework**: Python, Flask
* **Chess Logic**: python-chess (Backend), chess.js (Frontend)
* **Artificial Intelligence**: google-generativeai
* **Frontend UI**: HTML5, CSS3, JavaScript, chessboard.js
* **Markdown Rendering**: marked.js for formatting AI analysis reports

## Getting Started

### Prerequisites

Ensure you have Python 3.x installed on your system. You will also need a valid API key for Google Generative AI to utilize the analysis and dynamic opening features.

### Installation

1. Clone this repository to your local machine.
2. Navigate to the project directory.
3. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt

4. Configure your Google Generative AI API key within your environment variables (or directly within the logic files if configured that way).

5. Start the Flask server:

   ```bash
    python app.py
Open your web browser and navigate to http://127.0.0.1:5000/.


### Project Structure

* **app.py**: The main Flask application that handles routing, API endpoints, and client-server communication.

* **game_logic.py**: Contains the core logic for the chess trainer, including ELO tracking, AI integrations, and move handling.

* **templates/**: Contains the HTML templates for the user interface (index.html, openings.html, puzzles.html).

* **static/**: Contains the application's CSS styles, client-side JavaScript logic, and image assets.
