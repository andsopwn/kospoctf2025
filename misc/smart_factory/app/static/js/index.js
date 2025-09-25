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

async function fetchManufactStatus() {
    try {
        const response = await fetch('/api/manufact');
        if (!response.ok) throw new Error('네트워크 응답 오류');
        const data = await response.json();
        updateManufactStatus(data);
    } catch (error) {
        console.error('데이터 로드 실패:', error);
    }
}

function updateManufactStatus(data) {
    const container = document.getElementById('manufact-status');
    container.innerHTML = '';

    const allLines = [];
    for (const category in data) {
        const lines = data[category];
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
    div.style.position = 'relative';

    const categorySpan = document.createElement('span');
    categorySpan.textContent = line.category;
    categorySpan.style.position = 'absolute';
    categorySpan.style.top = '8px';
    categorySpan.style.left = '10px';
    categorySpan.style.fontWeight = 'bold';
    categorySpan.style.fontSize = '1em';

    const statusSpan = document.createElement('span');
    statusSpan.textContent = `${line.coord} : ${line.status ? '동작' : '정지'}`;
    statusSpan.style.position = 'absolute';
    statusSpan.style.bottom = '8px';
    statusSpan.style.right = '10px';
    statusSpan.style.fontSize = '0.9em';

    div.appendChild(categorySpan);
    div.appendChild(statusSpan);

    return div;
}

fetchManufactStatus();
setInterval(fetchManufactStatus, 5000);