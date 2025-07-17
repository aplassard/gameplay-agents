document.addEventListener('DOMContentLoaded', () => {    const socket = io();    const startButton = document.getElementById('start-button');    const dateInput = document.getElementById('date-input');    const modelInput = document.getElementById('model-input');    const gameStateDiv = document.getElementById('game-state');    const llmPromptDiv = document.getElementById('llm-prompt');    const llmResponseDiv = document.getElementById('llm-response');    
    const pauseButton = document.getElementById('pause-button');
    let isPaused = false;

    startButton.addEventListener('click', () => {
        const date = dateInput.value;
        const model = modelInput.value;
        socket.emit('start_game', { date, model });
        startButton.style.display = 'none';
        pauseButton.style.display = 'inline-block';
    });

    pauseButton.addEventListener('click', () => {
        isPaused = !isPaused;
        pauseButton.textContent = isPaused ? 'Resume' : 'Pause';
        socket.emit('pause_game', { 'paused': isPaused });
    });
;    socket.on('game_state', (data) => {        gameStateDiv.innerHTML = `<h2>Game State</h2><pre>${data.game_text}</pre>`;        if (data.clues) {            gameStateDiv.innerHTML += `<h3>Active Clues:</h3><ul>${data.clues.map(clue => `<li><b>${clue.id}:</b> ${clue.text}</li>`).join('')}</ul>`;        }        if (data.step_count) {            gameStateDiv.innerHTML += `<p>Steps: ${data.step_count}</p>`;        }    });    socket.on('llm_prompt', (data) => {        llmPromptDiv.innerHTML = `<h3>LLM Prompt</h3><pre>${data.prompt}</pre>`;    });    socket.on('llm_response', (data) => {        let content = `<h3>LLM Response</h3>`;        if (data.healed) {            content += `<strong>(Healed)</strong>`;        }        content += `<pre>${data.response}</pre>`;        llmResponseDiv.innerHTML = content;    });    socket.on('clue_answered', (data) => {        const result = data.correct ? 'Correct' : 'Incorrect';        llmResponseDiv.innerHTML += `<p>Answered clue ${data.clue_id} with "${data.answer}". Result: ${result}</p>`;    });    socket.on('game_over', (data) => {        const message = data.won ? 'You won!' : 'Game over!';        gameStateDiv.innerHTML += `<h2>${message}</h2><p>Total steps: ${data.steps}</p>`;    });    socket.on('error', (data) => {        alert(`Error: ${data.message}`);    });});