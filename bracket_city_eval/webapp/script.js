async function fetchData() {
    const response = await fetch('data/results.json');
    const data = await response.json();
    return data;
}

function aggregateData(allResults) {
    const aggregatedResults = {};
    const dailyCompletion = {};

    allResults.forEach(result => {
        const modelNameFull = result.model_name;
        const modelProvider = result.model_provider || 'unknown'; // Default to 'unknown' if not present
        const modelNameShort = result.model_name; // This will be the part after the slash
        const puzzleDate = result.puzzle_date;

        // Aggregate by model
        if (!aggregatedResults[modelNameFull]) {
            aggregatedResults[modelNameFull] = {
                modelProvider: modelProvider,
                modelName: modelNameShort,
                totalGames: 0,
                completedGames: 0,
                totalSteps: 0,
                totalDuration: 0,
                totalCost: 0,
                totalPromptTokens: 0,
                totalCompletionTokens: 0
            };
        }

        aggregatedResults[modelNameFull].totalGames++;
        if (result.game_completed) {
            aggregatedResults[modelNameFull].completedGames++;
        }
        aggregatedResults[modelNameFull].totalSteps += result.number_of_steps;
        
        if (result.start_time && result.end_time) {
            aggregatedResults[modelNameFull].totalDuration += (result.end_time - result.start_time);
        }
        
        aggregatedResults[modelNameFull].totalCost += result.total_cost;
        aggregatedResults[modelNameFull].totalPromptTokens += result.prompt_tokens;
        aggregatedResults[modelNameFull].totalCompletionTokens += result.completion_tokens;

        // Aggregate by date for completion rate
        if (!dailyCompletion[puzzleDate]) {
            dailyCompletion[puzzleDate] = {
                totalGames: 0,
                completedGames: 0
            };
        }
        dailyCompletion[puzzleDate].totalGames++;
        if (result.game_completed) {
            dailyCompletion[puzzleDate].completedGames++;
        }
    });

    return { aggregatedResults, dailyCompletion };
}

function renderTable(aggregatedResults) {
    let tableHTML = '<table>';
    tableHTML += '<thead><tr>' +
                 '<th id="sort-modelProvider" class="sortable" data-sort="modelProvider">Model Provider</th>' +
                 '<th id="sort-modelName" class="sortable" data-sort="modelName">Model Name</th>' +
                 '<th id="sort-totalGames" class="sortable" data-sort="totalGames">Games Run</th>' +
                 '<th id="sort-completedGames" class="sortable" data-sort="completedGames">Games Completed</th>' +
                 '<th id="sort-successRate" class="sortable" data-sort="successRate">Success Rate (%)</th>' +
                 '<th id="sort-avgSteps" class="sortable" data-sort="avgSteps">Avg Steps</th>' +
                 '<th id="sort-avgDuration" class="sortable" data-sort="avgDuration">Avg Duration (s)</th>' +
                 '<th id="sort-avgCost" class="sortable" data-sort="avgCost">Avg Cost ($)</th>' +
                 '<th id="sort-avgPromptTokens" class="sortable" data-sort="avgPromptTokens">Avg Prompt Tokens</th>' +
                 '<th id="sort-avgCompletionTokens" class="sortable" data-sort="avgCompletionTokens">Avg Completion Tokens</th>' +
                 '</tr></thead>';
    tableHTML += '<tbody>';

    const aggregatedResultsArray = Object.values(aggregatedResults);

    aggregatedResultsArray.forEach(stats => {
        const successRate = (stats.completedGames / stats.totalGames) * 100 || 0;
        const avgSteps = stats.totalSteps / stats.totalGames || 0;
        const avgDuration = stats.totalDuration / stats.totalGames || 0;
        const avgCost = stats.totalCost / stats.totalGames || 0;
        const avgPromptTokens = stats.totalPromptTokens / stats.totalGames || 0;
        const avgCompletionTokens = stats.totalCompletionTokens / stats.totalGames || 0;

        tableHTML += `
            <tr>
                <td>${stats.modelProvider}</td>
                <td>${stats.modelName}</td>
                <td>${stats.totalGames}</td>
                <td>${stats.completedGames}</td>
                <td>${successRate.toFixed(2)}</td>
                <td>${avgSteps.toFixed(2)}</td>
                <td>${avgDuration.toFixed(2)}</td>
                <td>${avgCost.toFixed(4)}</td>
                <td>${avgPromptTokens.toFixed(0)}</td>
                <td>${avgCompletionTokens.toFixed(0)}</td>
            </tr>
        `;
    });

    tableHTML += '</tbody></table>';
    document.getElementById('results-table').innerHTML = tableHTML;

    // Add sort event listeners
    document.querySelectorAll('#results-table th.sortable').forEach(header => {
        header.addEventListener('click', () => {
            const sortBy = header.dataset.sort;
            const currentOrder = header.dataset.order || 'asc';
            const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';

            // Remove existing order indicators
            document.querySelectorAll('#results-table th.sortable').forEach(h => {
                h.removeAttribute('data-order');
                h.classList.remove('asc', 'desc');
            });

            // Set new order indicator
            header.dataset.order = newOrder;
            header.classList.add(newOrder);

            sortAndRenderTable(sortBy, newOrder);
        });
    });
}



function sortAndRenderTable(sortBy, order) {
    currentSortBy = sortBy;
    currentSortOrder = order;

    const aggregatedResultsArray = Object.values(window.lastAggregatedResults);

    aggregatedResultsArray.sort((a, b) => {
        let valA = a[sortBy];
        let valB = b[sortBy];

        // Handle calculated fields for sorting
        if (sortBy === 'successRate') {
            valA = (a.completedGames / a.totalGames) * 100 || 0;
            valB = (b.completedGames / b.totalGames) * 100 || 0;
        } else if (sortBy === 'avgSteps') {
            valA = a.totalSteps / a.totalGames || 0;
            valB = b.totalSteps / b.totalGames || 0;
        } else if (sortBy === 'avgDuration') {
            valA = a.totalDuration / a.totalGames || 0;
            valB = b.totalDuration / b.totalGames || 0;
        } else if (sortBy === 'avgCost') {
            valA = a.totalCost / a.totalGames || 0;
            valB = b.totalCost / b.totalGames || 0;
        } else if (sortBy === 'avgPromptTokens') {
            valA = a.totalPromptTokens / a.totalGames || 0;
            valB = b.totalPromptTokens / b.totalGames || 0;
        } else if (sortBy === 'avgCompletionTokens') {
            valA = a.totalCompletionTokens / a.totalGames || 0;
            valB = b.totalCompletionTokens / b.totalGames || 0;
        }

        if (typeof valA === 'string') {
            return order === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        } else {
            return order === 'asc' ? valA - valB : valB - valA;
        }
    });

    renderTable(aggregatedResultsArray.reduce((obj, item) => (obj[item.modelNameFull] = item, obj), {}));
}

function renderDailyCompletionGraph(dailyCompletion) {
    const dates = Object.keys(dailyCompletion).sort();
    const completionRates = dates.map(date => {
        const dailyStats = dailyCompletion[date];
        return (dailyStats.completedGames / dailyStats.totalGames) * 100 || 0;
    });

    const trace = {
        x: dates,
        y: completionRates,
        mode: 'lines+markers',
        type: 'scatter',
        name: 'Completion Rate',
        line: { color: '#17BECF' }
    };

    const layout = {
        title: 'Daily Completion Rate',
        xaxis: { title: 'Date' },
        yaxis: { title: 'Completion Rate (%)' }
    };

    Plotly.newPlot('daily-completion-graph', [trace], layout);
}

function renderCompletionTokensVsSuccessRateGraph(aggregatedResults) {
    const scatterX = [];
    const scatterY = [];
    const scatterText = [];

    for (const modelNameFull in aggregatedResults) {
        const stats = aggregatedResults[modelNameFull];
        const successRate = (stats.completedGames / stats.totalGames) * 100 || 0;
        const avgCompletionTokens = stats.totalCompletionTokens / stats.totalGames || 0;

        scatterX.push(avgCompletionTokens);
        scatterY.push(successRate);
        scatterText.push(`${stats.modelProvider}/${stats.modelName}`);
    }

    const scatterTrace = {
        x: scatterX,
        y: scatterY,
        mode: 'markers+text',
        type: 'scatter',
        text: scatterText,
        textposition: 'top center',
        marker: { size: 10 }
    };

    const scatterLayout = {
        title: 'Completion Rate vs. Average Completion Tokens by Model',
        xaxis: { title: 'Average Completion Tokens', type: 'log' },
        yaxis: { title: 'Success Rate (%)' }
    };

    Plotly.newPlot('completion-tokens-vs-success-rate-graph', [scatterTrace], scatterLayout);
}

function renderDurationVsCompletionRateGraph(aggregatedResults) {
    const scatterX = [];
    const scatterY = [];
    const scatterText = [];

    for (const modelNameFull in aggregatedResults) {
        const stats = aggregatedResults[modelNameFull];
        const successRate = (stats.completedGames / stats.totalGames) * 100 || 0;
        const avgDuration = stats.totalDuration / stats.totalGames || 0;

        scatterX.push(avgDuration);
        scatterY.push(successRate);
        scatterText.push(`${stats.modelProvider}/${stats.modelName}`);
    }

    const scatterTrace = {
        x: scatterX,
        y: scatterY,
        mode: 'markers+text',
        type: 'scatter',
        text: scatterText,
        textposition: 'top center',
        marker: { size: 10 }
    };

    const scatterLayout = {
        title: 'Duration vs. Completion Rate by Model',
        xaxis: { title: 'Average Duration (s)' },
        yaxis: { title: 'Success Rate (%)' }
    };

    Plotly.newPlot('duration-vs-completion-rate-graph', [scatterTrace], scatterLayout);
}

async function init() {
    const allResults = await fetchData();
    const { aggregatedResults, dailyCompletion } = aggregateData(allResults);
    window.lastAggregatedResults = aggregatedResults; // Store for sorting
    renderTable(aggregatedResults);
    renderDailyCompletionGraph(dailyCompletion);
    renderCompletionTokensVsSuccessRateGraph(aggregatedResults);
    renderDurationVsCompletionRateGraph(aggregatedResults);
    renderSpecificDateTable('2025-05-14', allResults);
}

init();

function renderSpecificDateTable(date, allResults) {
    const filteredResults = allResults.filter(result => result.puzzle_date === date);

    const aggregatedSpecificResults = {};

    filteredResults.forEach(result => {
        const modelNameFull = result.model_name;
        const modelProvider = result.model_provider || 'unknown';
        const modelNameShort = result.model_name;

        if (!aggregatedSpecificResults[modelNameFull]) {
            aggregatedSpecificResults[modelNameFull] = {
                modelProvider: modelProvider,
                modelName: modelNameShort,
                totalGames: 0,
                completedGames: 0,
                totalSteps: 0,
                totalDuration: 0,
                totalCost: 0,
                totalPromptTokens: 0,
                totalCompletionTokens: 0
            };
        }

        aggregatedSpecificResults[modelNameFull].totalGames++;
        if (result.game_completed) {
            aggregatedSpecificResults[modelNameFull].completedGames++;
        }
        aggregatedSpecificResults[modelNameFull].totalSteps += result.number_of_steps;
        
        if (result.start_time && result.end_time) {
            aggregatedSpecificResults[modelNameFull].totalDuration += (result.end_time - result.start_time);
        }
        
        aggregatedSpecificResults[modelNameFull].totalCost += result.total_cost;
        aggregatedSpecificResults[modelNameFull].totalPromptTokens += result.prompt_tokens;
        aggregatedSpecificResults[modelNameFull].totalCompletionTokens += result.completion_tokens;
    });

    let tableHTML = '<table>';
    tableHTML += '<thead><tr><th>Model Provider</th><th>Model Name</th><th>Games Run</th><th>Games Completed</th><th>Success Rate (%)</th><th>Avg Steps</th><th>Avg Duration (s)</th><th>Avg Cost ($)</th><th>Avg Prompt Tokens</th><th>Avg Completion Tokens</th></tr></thead>';
    tableHTML += '<tbody>';

    for (const modelNameFull in aggregatedSpecificResults) {
        const stats = aggregatedSpecificResults[modelNameFull];
        const successRate = (stats.completedGames / stats.totalGames) * 100 || 0;
        const avgSteps = stats.totalSteps / stats.totalGames || 0;
        const avgDuration = stats.totalDuration / stats.totalGames || 0;
        const avgCost = stats.totalCost / stats.totalGames || 0;
        const avgPromptTokens = stats.totalPromptTokens / stats.totalGames || 0;
        const avgCompletionTokens = stats.totalCompletionTokens / stats.totalGames || 0;

        tableHTML += `
            <tr>
                <td>${stats.modelProvider}</td>
                <td>${stats.modelName}</td>
                <td>${stats.totalGames}</td>
                <td>${stats.completedGames}</td>
                <td>${successRate.toFixed(2)}</td>
                <td>${avgSteps.toFixed(2)}</td>
                <td>${avgDuration.toFixed(2)}</td>
                <td>${avgCost.toFixed(4)}</td>
                <td>${avgPromptTokens.toFixed(0)}</td>
                <td>${avgCompletionTokens.toFixed(0)}</td>
            </tr>
        `;
    }

    tableHTML += '</tbody></table>';
    document.getElementById('results-2025-05-14-table').innerHTML = tableHTML;
}