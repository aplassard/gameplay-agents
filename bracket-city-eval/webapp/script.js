let allData = [];

async function fetchData() {
    const response = await fetch('data/results.json');
    allData = await response.json();
    return allData;
}

function populateFilters(data) {
    const modelFilter = document.getElementById('model-filter');
    const dateFilter = document.getElementById('date-filter');

    const models = [...new Set(data.map(d => d.model_name))].sort();
    const dates = [...new Set(data.map(d => d.puzzle_date))].sort();

    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        modelFilter.appendChild(option);
    });

    dates.forEach(date => {
        const option = document.createElement('option');
        option.value = date;
        option.textContent = date;
        dateFilter.appendChild(option);
    });

    modelFilter.addEventListener('change', updateCharts);
    dateFilter.addEventListener('change', updateCharts);
}

function filterData() {
    const modelFilter = document.getElementById('model-filter');
    const dateFilter = document.getElementById('date-filter');

    const selectedModels = Array.from(modelFilter.selectedOptions).map(option => option.value);
    const selectedDates = Array.from(dateFilter.selectedOptions).map(option => option.value);

    let filtered = allData;

    if (selectedModels.length > 0) {
        filtered = filtered.filter(d => selectedModels.includes(d.model_name));
    }

    if (selectedDates.length > 0) {
        filtered = filtered.filter(d => selectedDates.includes(d.puzzle_date));
    }

    return filtered;
}

function updateCharts() {
    const filteredData = filterData();
    createCharts(filteredData);
}

function createCharts(data) {
    const models = [...new Set(data.map(d => d.model_name))];

    // Success Rate
    const successRateData = models.map(model => {
        const modelData = data.filter(d => d.model_name === model);
        const completed = modelData.filter(d => d.game_completed).length;
        return (completed / modelData.length) * 100;
    });

    const successRateTrace = {
        x: models,
        y: successRateData,
        type: 'bar',
        marker: { color: 'rgba(75, 192, 192, 0.6)' }
    };
    const successRateLayout = { title: 'Success Rate by Model', yaxis: { title: 'Success Rate (%)' } };
    Plotly.newPlot('success-rate-chart', [successRateTrace], successRateLayout);

    // Average Steps
    const avgStepsData = models.map(model => {
        const modelData = data.filter(d => d.model_name === model && d.game_completed);
        const totalSteps = modelData.reduce((sum, d) => sum + d.number_of_steps, 0);
        return totalSteps / modelData.length;
    });

    const avgStepsTrace = {
        x: models,
        y: avgStepsData,
        type: 'bar',
        marker: { color: 'rgba(255, 159, 64, 0.6)' }
    };
    const avgStepsLayout = { title: 'Average Steps per Completed Game', yaxis: { title: 'Average Steps' } };
    Plotly.newPlot('avg-steps-chart', [avgStepsTrace], avgStepsLayout);

    // Average Duration
    const avgDurationData = models.map(model => {
        const modelData = data.filter(d => d.model_name === model);
        const totalDuration = modelData.reduce((sum, d) => sum + (d.end_time - d.start_time), 0);
        return totalDuration / modelData.length;
    });

    const avgDurationTrace = {
        x: models,
        y: avgDurationData,
        type: 'bar',
        marker: { color: 'rgba(153, 102, 255, 0.6)' }
    };
    const avgDurationLayout = { title: 'Average Run Duration by Model', yaxis: { title: 'Average Duration (s)' } };
    Plotly.newPlot('avg-duration-chart', [avgDurationTrace], avgDurationLayout);

    // Average Cost
    const avgCostData = models.map(model => {
        const modelData = data.filter(d => d.model_name === model && d.game_completed);
        const totalCost = modelData.reduce((sum, d) => sum + d.total_cost, 0);
        return totalCost / modelData.length;
    });

    const avgCostTrace = {
        x: models,
        y: avgCostData,
        type: 'bar',
        marker: { color: 'rgba(255, 99, 132, 0.6)' }
    };
    const avgCostLayout = { title: 'Average Cost per Completed Game', yaxis: { title: 'Average Cost ($)' } };
    Plotly.newPlot('avg-cost-chart', [avgCostTrace], avgCostLayout);

    // Token Usage
    const tokenUsagePromptData = models.map(model => {
        const modelData = data.filter(d => d.model_name === model);
        return modelData.reduce((sum, d) => sum + d.prompt_tokens, 0) / modelData.length;
    });
    const tokenUsageCompletionData = models.map(model => {
        const modelData = data.filter(d => d.model_name === model);
        return modelData.reduce((sum, d) => sum + d.completion_tokens, 0) / modelData.length;
    });

    const tokenUsageTracePrompt = {
        x: models,
        y: tokenUsagePromptData,
        name: 'Average Prompt Tokens',
        type: 'bar',
        marker: { color: 'rgba(54, 162, 235, 0.6)' }
    };
    const tokenUsageTraceCompletion = {
        x: models,
        y: tokenUsageCompletionData,
        name: 'Average Completion Tokens',
        type: 'bar',
        marker: { color: 'rgba(255, 206, 86, 0.6)' }
    };
    const tokenUsageLayout = { barmode: 'group', title: 'Token Usage by Model', yaxis: { title: 'Average Tokens' } };
    Plotly.newPlot('token-usage-chart', [tokenUsageTracePrompt, tokenUsageTraceCompletion], tokenUsageLayout);

    // Completion Rate by Date
    const dates = [...new Set(data.map(d => d.puzzle_date))].sort();
    const completionRateByDateData = dates.map(date => {
        const dateData = data.filter(d => d.puzzle_date === date);
        const completed = dateData.filter(d => d.game_completed).length;
        return (completed / dateData.length) * 100;
    });

    const completionRateByDateTrace = {
        x: dates,
        y: completionRateByDateData,
        mode: 'lines+markers',
        type: 'scatter',
        line: { color: 'rgba(75, 192, 192, 1)' }
    };
    const completionRateByDateLayout = { title: 'Completion Rate by Date', yaxis: { title: 'Completion Rate (%)' } };
    Plotly.newPlot('completion-rate-by-date-chart', [completionRateByDateTrace], completionRateByDateLayout);
}

async function init() {
    await fetchData();
    populateFilters(allData);
    updateCharts();
}

init();