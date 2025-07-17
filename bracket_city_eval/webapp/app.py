
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import sys
import os

# Add the parent directory to the Python path to import the game logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bracket_city_mcp.puzzle_loader import load_game_data_by_date
from bracket_city_mcp.game.game import Game
from graph import build_llm_message, parse_llm_response, heal_llm_output
from llm_utils import call_llm_with_retry

app = Flask(__name__, template_folder='templates', static_folder='static')
socketio = SocketIO(app, cors_allowed_origins="*")

game_paused = False

@app.route('/')
def index():
    return render_template('index.html')

def get_clues_with_text(game_instance):
    return [{'id': clue_id, 'text': game_instance.clues.get(clue_id).get_rendered_text(game_instance)} for clue_id in game_instance.active_clues]

@socketio.on('pause_game')
def handle_pause_game(data):
    global game_paused
    game_paused = data.get('paused', False)

@socketio.on('start_game')
def handle_start_game(data):
    global game_paused
    game_paused = False

    date_str = data.get('date')
    model_name = data.get('model')

    if not date_str or not model_name:
        emit('error', {'message': 'Date and model are required.'})
        return

    try:
        game = Game(load_game_data_by_date(date_str))
        emit('game_state', {'game_text': game.get_rendered_game_text(), 'clues': get_clues_with_text(game)})

        step_count = 0
        max_steps = 100  # You can make this configurable

        while not game.is_complete and step_count < max_steps:
            while game_paused:
                socketio.sleep(1)

            llm_message = build_llm_message(game)
            emit('llm_prompt', {'prompt': llm_message})

            llm_response = call_llm_with_retry(
                model_name=model_name,
                prompt_message=llm_message
            )
            emit('llm_response', {'response': llm_response})

            clue_id, answer = parse_llm_response(llm_response)

            if clue_id is None or answer is None:
                try:
                    healed_response = heal_llm_output(llm_response)
                    clue_id, answer = parse_llm_response(healed_response)
                    emit('llm_response', {'response': healed_response, 'healed': True})
                except Exception as e:
                    emit('error', {'message': f'LLM healing failed: {e}'})


            if clue_id and answer:
                if game.clues.get(clue_id):
                    game.answer_clue(clue_id, answer)
                    emit('clue_answered', {'clue_id': clue_id, 'answer': answer, 'correct': game.clues.get(clue_id).completed})
                else:
                    emit('error', {'message': f'Clue with id {clue_id} not found.'})

            step_count += 1
            emit('game_state', {'game_text': game.get_rendered_game_text(), 'clues': get_clues_with_text(game), 'step_count': step_count})
            socketio.sleep(1) # Add a small delay to allow the UI to update

        emit('game_over', {'won': game.is_complete, 'steps': step_count})

    except Exception as e:
        emit('error', {'message': str(e)})

if __name__ == '__main__':
    socketio.run(app, debug=True)
