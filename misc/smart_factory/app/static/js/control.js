let productionChart = null;

function parseCoordinate(coord) {
    const parts = coord.split('-').map(Number);
    return parts;
}

function compareCoordinates(a, b) {
    const [aRow, aCol] = parseCoordinate(a);
    const [bRow, bCol] = parseCoordinate(b);
    if (aRow !== bRow) return aRow - bRow;
    return aCol - bCol;
}

async function fetchProductionStatus() {
    try {
        const response = await fetch('/api/production_status');
        if (!response.ok) throw new Error('네트워크 응답 오류');
        const data = await response.json();

        if (document.getElementById('manufact-status')) {
            updateManufactStatus(data.manufact_lines);
        }
        if (document.getElementById('summary-dashboard')) {
            updateSummaryDashboard(data.summary);
        }
        if (document.getElementById('production-chart')) {
            updateProductionChart(data.summary);
        }

        if (document.getElementById('line-toggles')) {
            renderLineToggles(data.manufact_lines);
        }
        if (document.getElementById('material-target-settings')) {
            renderMaterialTargetSettings(data.material_targets);
        }

    } catch (error) {
        console.error('데이터 로드 실패:', error);
    }
}

function updateSummaryDashboard(summary) {
    const summaryContainer = document.getElementById('summary-dashboard');
    if (!summaryContainer) return;

    summaryContainer.innerHTML = '';

    const summaries = [
        { title: '오늘 생산량', value: summary.total_produced_today, unit: '개', class: 'green' },
        { title: '일일 목표량', value: summary.daily_target, unit: '개', class: '' },
        { title: '현재 효율', value: summary.current_efficiency, unit: '%', class: (summary.current_efficiency < 80 ? 'red' : 'green') },
        { title: '미해결 오류', value: summary.unresolved_errors, unit: '건', class: (summary.unresolved_errors > 0 ? 'red' : 'green') }
    ];

    summaries.forEach(item => {
        const box = document.createElement('div');
        box.className = `summary-box ${item.class}`;
        box.innerHTML = `
            <h3>${item.title}</h3>
            <div class="value">${item.value}<span>${item.unit}</span></div>
        `;
        summaryContainer.appendChild(box);
    });
}

function updateManufactStatus(manufact_lines) {
    const container = document.getElementById('manufact-status');
    if (!container) return;

    container.innerHTML = '';

    const allLines = [];
    for (const category in manufact_lines) {
        const lines = manufact_lines[category];
        for (const coord in lines) {
            allLines.push({
                category,
                coord,
                status: lines[coord]
            });
        }
    }

    allLines.sort((a, b) => compareCoordinates(a.coord, b.coord));

    for (let i = 0; i < allLines.length; i += 2) {
        const lineBox = document.createElement('div');
        lineBox.className = 'line-box';

        const line1 = allLines[i];
        const line1Div = createLineStatusDiv(line1);
        lineBox.appendChild(line1Div);

        if (i + 1 < allLines.length) {
            const line2 = allLines[i + 1];
            const line2Div = createLineStatusDiv(line2);
            lineBox.appendChild(line2Div);
        } else {
            const emptyDiv = document.createElement('div');
            emptyDiv.style.width = '48%';
            lineBox.appendChild(emptyDiv);
        }

        container.appendChild(lineBox);
    }
}

function createLineStatusDiv(line) {
    const div = document.createElement('div');
    div.className = 'line-status ' + (line.status ? 'status-on' : 'status-off');

    const categorySpan = document.createElement('span');
    categorySpan.className = 'category-name';
    categorySpan.textContent = line.category;

    const statusSpan = document.createElement('span');
    statusSpan.className = 'coord-status';
    statusSpan.textContent = `${line.coord} : ${line.status ? '동작' : '정지'}`;

    div.appendChild(categorySpan);
    div.appendChild(statusSpan);

    return div;
}

function updateProductionChart(summary) {
    const ctx = document.getElementById('production-chart');
    if (!ctx) return;

    const chartData = {
        labels: ['생산량', '목표량'],
        datasets: [{
            label: '오늘의 생산 목표 달성 현황',
            data: [summary.total_produced_today, summary.daily_target],
            backgroundColor: [
                'rgba(40, 167, 69, 0.6)',
                'rgba(0, 123, 255, 0.6)'
            ],
            borderColor: [
                'rgba(40, 167, 69, 1)',
                'rgba(0, 123, 255, 1)'
            ],
            borderWidth: 1
        }]
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                title: {
                    display: true,
                    text: '수량 (개)'
                }
            }
        }
    };

    if (productionChart) {
        productionChart.data = chartData;
        productionChart.update();
    } else {
        productionChart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: chartOptions
        });
    }
}

function renderLineToggles(manufact_lines) {
    const lineTogglesContainer = document.getElementById('line-toggles');
    if (!lineTogglesContainer) return;

    lineTogglesContainer.innerHTML = '';

    const allLines = [];
    for (const material in manufact_lines) {
        for (const coordinate in manufact_lines[material]) {
            allLines.push({
                material,
                coordinate,
                status: manufact_lines[material][coordinate]
            });
        }
    }

    allLines.sort((a, b) => compareCoordinates(a.coordinate, b.coordinate));

    allLines.forEach(line => {
        const toggleItem = document.createElement('div');
        toggleItem.className = 'line-toggle-item';
        toggleItem.innerHTML = `
            <span class="line-toggle-label">${line.material} ${line.coordinate}</span>
            <label class="switch">
                <input type="checkbox" id="toggle-${line.material}-${line.coordinate}" ${line.status ? 'checked' : ''}>
                <span class="slider"></span>
            </label>
        `;
        lineTogglesContainer.appendChild(toggleItem);

        const toggleInput = document.getElementById(`toggle-${line.material}-${line.coordinate}`);
        toggleInput.addEventListener('change', (event) => {
            updateLineStatusOnServer(line.material, line.coordinate, event.target.checked);
        });
    });
}

async function updateLineStatusOnServer(material, coordinate, enabled) {
    try {
        const response = await fetch('/api/line_control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ material, coordinate, enabled }),
        });
        const data = await response.json();
        if (data.status === 'success') {
            console.log(`Line ${material} ${coordinate} status updated to ${enabled}.`);
        } else {
            console.error(`Failed to update line status: ${data.message}`);
            alert(`Failed to update line ${material} ${coordinate} status: ${data.message}`);
        }
    } catch (error) {
        console.error('Error updating line status:', error);
        alert('Network error during line status update.');
    }
}

function renderMaterialTargetSettings(material_targets) {
    const targetSettingsContainer = document.getElementById('material-target-settings');
    if (!targetSettingsContainer) return;

    targetSettingsContainer.innerHTML = '';

    for (const material in material_targets) {
        const settingItem = document.createElement('div');
        settingItem.className = 'target-setting-item';
        settingItem.innerHTML = `
            <label for="target-${material}">${material.charAt(0).toUpperCase() + material.slice(1)}:</label>
            <input type="number" id="target-${material}" value="${material_targets[material]}" min="0">
            <button data-material="${material}">설정</button>
        `;
        targetSettingsContainer.appendChild(settingItem);

        const setButton = settingItem.querySelector('button');
        setButton.addEventListener('click', async () => {
            const inputElement = document.getElementById(`target-${material}`);
            const newTarget = parseInt(inputElement.value, 10);

            if (isNaN(newTarget) || newTarget < 0) {
                alert('유효한 생산 목표량을 입력해주세요 (0 이상의 숫자).');
                return;
            }

            try {
                const response = await fetch('/api/set_target', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ material: material, target_amount: newTarget }),
                });
                const data = await response.json();
                if (data.status === 'success') {
                    alert(`${material.charAt(0).toUpperCase() + material.slice(1)} 목표량이 ${newTarget}으로 설정되었습니다.`);
                } else {
                    alert(`생산 목표량 설정 실패: ${data.message}`);
                }
            } catch (error) {
                console.error('생산 목표량 설정 중 오류:', error);
                alert('생산 목표량 설정 중 네트워크 오류가 발생했습니다.');
            }
        });
    }
}


const calculator = document.querySelector('.calculator');
const display = document.getElementById('calculator-display');

let currentExpression = '0';
let resetDisplayOnNextInput = false;

function updateDisplay() {
    display.textContent = currentExpression;
}

function handleNumber(number) {
    if (resetDisplayOnNextInput) {
        currentExpression = number === '.' ? '0.' : number;
        resetDisplayOnNextInput = false;
    } else if (currentExpression === '0' && number !== '.') {
        currentExpression = number;
    } else {
        currentExpression += number;
    }
    updateDisplay();
}

function handleOperator(op) {
    const operators = ['+', '-', '×', '÷'];
    if (currentExpression === '0' && operators.includes(op)) {
        return; // Don't start with operator unless it's a negative sign
    }

    if (operators.some(operator => currentExpression.endsWith(operator))) {
        currentExpression = currentExpression.slice(0, -1) + op;
    } else {
        currentExpression += op;
    }
    updateDisplay();
    resetDisplayOnNextInput = false;
}

async function calculateResult() {
    try {
        const expressionToSend = currentExpression.replace(/×/g, '*').replace(/÷/g, '/');
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ expression: expressionToSend }),
        });
        const data = await response.json();

        if (data.result !== undefined) {
            currentExpression = String(data.result);
            updateDisplay();
            resetDisplayOnNextInput = true;
        } else if (data.error) {
            currentExpression = 'Error';
            updateDisplay();
            console.error('Calculation error:', data.error);
            resetDisplayOnNextInput = true;
        }
    } catch (error) {
        currentExpression = 'Error';
        updateDisplay();
        console.error('Network or parsing error:', error);
        resetDisplayOnNextInput = true;
    }
}

function clearCalculator() {
    currentExpression = '0';
    resetDisplayOnNextInput = false;
    updateDisplay();
}

if (calculator) {
    calculator.addEventListener('click', (event) => {
        const { target } = event;
        if (!target.matches('button')) {
            return;
        }

        if (target.classList.contains('number') || target.classList.contains('decimal')) {
            handleNumber(target.textContent);
        } else if (target.classList.contains('operator')) {
            handleOperator(target.textContent);
        } else if (target.classList.contains('equal')) {
            calculateResult();
        } else if (target.classList.contains('clear')) {
            clearCalculator();
        }
    });
}

fetchProductionStatus();
setInterval(fetchProductionStatus, 5000);