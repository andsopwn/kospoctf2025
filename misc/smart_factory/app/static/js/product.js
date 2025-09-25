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

        updateManufactStatus(data.manufact_lines);

        updateSummaryDashboard(data.summary);

        updateProductionChart(data.summary);

    } catch (error) {
        console.error('데이터 로드 실패:', error);
    }
}

function updateSummaryDashboard(summary) {
    const summaryContainer = document.getElementById('summary-dashboard');
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
    const ctx = document.getElementById('production-chart').getContext('2d');

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

fetchProductionStatus();
setInterval(fetchProductionStatus, 5000);