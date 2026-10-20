(function () {
    'use strict';

    const data = JSON.parse(document.getElementById('report-data').textContent);

    const SAGE = '#8fa382';
    const LAVENDER = '#a394bd';
    const BLUE = '#6f9aa8';

    function themeColors() {
        const cs = getComputedStyle(document.body);
        return {
            grid: cs.getPropertyValue('--border').trim(),
            tick: cs.getPropertyValue('--text-dim').trim(),
            surface: cs.getPropertyValue('--surface').trim(),
            text: cs.getPropertyValue('--text').trim(),
        };
    }
    let C = themeColors();

    Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
    Chart.defaults.font.size = 11;
    Chart.defaults.color = C.tick;
    Chart.register(ChartDataLabels);
    Chart.defaults.plugins.datalabels.display = false;

    const fmtMin = (v) => {
        if (v <= 0) return '0m';
        const h = Math.floor(v / 60);
        const m = Math.round(v % 60);
        return h ? `${h}h${m ? ' ' + m + 'm' : ''}` : `${m}m`;
    };
    const fmtLabel = (v) => {
        if (v <= 0) return '';
        return fmtMin(v).replace(' ', '');
    };

    const axisBase = {
        grid: { color: C.grid },
        ticks: { maxRotation: 0 },
        border: { display: false },
    };
    const minAxis = {
        ...axisBase,
        beginAtZero: true,
        ticks: { callback: (v) => (v >= 60 ? `${v / 60}h` : `${v}m`), maxRotation: 0 },
    };
    const xAxis = { ...axisBase, grid: { display: false }, ticks: { autoSkip: true, maxTicksLimit: 15 } };

    const charts = [];

    // ---- Hero: study minutes per day (+ goal line) ----
    const barDatasets = [{
        label: 'Study time',
        data: data.bar.data,
        backgroundColor: SAGE,
        hoverBackgroundColor: '#7d9270',
        borderRadius: 4,
        maxBarThickness: 42,
    }];
    if (data.bar.goal > 0) {
        barDatasets.push({
            type: 'line',
            label: 'Daily goal',
            data: data.bar.data.map(() => data.bar.goal),
            borderColor: LAVENDER,
            borderWidth: 1.5,
            borderDash: [6, 5],
            pointRadius: 0,
            fill: false,
        });
    }
    const barChart = new Chart(document.getElementById('chart-bar'), {
        type: 'bar',
        data: { labels: data.bar.labels, datasets: barDatasets },
        options: {
            maintainAspectRatio: false,
            scales: { x: xAxis, y: minAxis },
            plugins: {
                legend: { display: data.bar.goal > 0, position: 'bottom', labels: { boxWidth: 12 } },
                tooltip: { callbacks: { label: (c) => ` ${c.dataset.label === 'Daily goal' ? 'Goal: ' + c.parsed.y + 'm' : fmtMin(c.parsed.y)}` } },
                datalabels: {
                    display: (c) => c.datasetIndex === 0 && c.dataset.data[c.dataIndex] > 0,
                    anchor: 'end', align: 'top', offset: -2,
                    color: '#6b7a5e', font: { size: 9, weight: '600' },
                    formatter: fmtLabel,
                },
            },
        },
    });
    charts.push(barChart);

    // ---- Donut: time by activity/task ----
    const donutEl = document.getElementById('chart-donut');
    const centerTextPlugin = {
        id: 'centerText',
        afterDraw(chart) {
            const { ctx, chartArea } = chart;
            const cx = (chartArea.left + chartArea.right) / 2;
            const cy = (chartArea.top + chartArea.bottom) / 2;
            ctx.save();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.font = '800 22px Inter, sans-serif';
            ctx.fillStyle = C.text;
            ctx.fillText(data.donut.total || '0m', cx, cy - (data.donut.single ? 12 : 6));
            ctx.font = '700 9px Inter, sans-serif';
            ctx.fillStyle = C.tick;
            ctx.fillText('TOTAL', cx, cy + (data.donut.single ? 6 : 14));
            if (data.donut.single) {
                ctx.font = '600 9px Inter, sans-serif';
                const note = `All ${data.donut.single}`;
                ctx.fillText(note.length > 18 ? note.slice(0, 17) + '…' : note, cx, cy + 20);
            }
            ctx.restore();
        },
    };
    const donutChart = new Chart(donutEl, {
        type: 'doughnut',
        data: {
            labels: data.donut.labels,
            datasets: [{
                data: data.donut.data,
                backgroundColor: data.donut.colors,
                borderColor: C.surface,
                borderWidth: 2,
            }],
        },
        plugins: [centerTextPlugin],
        options: {
            maintainAspectRatio: false,
            cutout: '68%',
            plugins: {
                legend: { display: false },
                datalabels: { display: false },
                tooltip: {
                    callbacks: {
                        label: (c) => {
                            const total = c.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total ? Math.round((c.parsed / total) * 100) : 0;
                            return ` ${fmtMin(c.parsed)} (${pct}%)`;
                        },
                    },
                },
            },
            onClick: (e, els) => {
                if (!els.length || !data.donut.slugs) return;
                const slug = data.donut.slugs[els[0].index];
                if (slug) {
                    const params = new URLSearchParams(location.search);
                    params.set('kind', slug);
                    window.location.href = `?${params.toString()}`;
                }
            },
            onHover: (e, els) => { e.native.target.style.cursor = els.length && data.donut.slugs ? 'pointer' : 'default'; },
        },
    });
    charts.push(donutChart);

    // HTML legend beside the donut
    const legendEl = document.getElementById('donut-legend');
    if (legendEl) {
        const total = data.donut.data.reduce((a, b) => a + b, 0);
        data.donut.labels.forEach((label, i) => {
            const pct = total ? Math.round((data.donut.data[i] / total) * 100) : 0;
            const li = document.createElement('li');
            li.innerHTML =
                `<span class="dl-dot" style="background:${data.donut.colors[i]}"></span>` +
                `<span class="dl-name">${label}</span>` +
                `<span class="dl-val">${fmtMin(data.donut.data[i])} · ${pct}%</span>`;
            if (data.donut.slugs && data.donut.slugs[i]) {
                li.style.cursor = 'pointer';
                li.title = 'Filter report by ' + label;
                li.addEventListener('click', () => {
                    const params = new URLSearchParams(location.search);
                    params.set('kind', data.donut.slugs[i]);
                    window.location.href = `?${params.toString()}`;
                });
            }
            legendEl.appendChild(li);
        });
    }

    // ---- Sessions per day ----
    const sessEl = document.getElementById('chart-sessions');
    if (sessEl) {
        charts.push(new Chart(sessEl, {
            type: 'bar',
            data: {
                labels: data.sessions.labels,
                datasets: [{
                    data: data.sessions.data,
                    backgroundColor: BLUE,
                    borderRadius: 4,
                    maxBarThickness: 34,
                }],
            },
            options: {
                maintainAspectRatio: false,
                scales: {
                    x: xAxis,
                    y: { ...axisBase, beginAtZero: true, suggestedMax: 4, ticks: { precision: 0 } },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: (items) => items[0].label,
                            label: (c) => ` ${c.parsed.y} session${c.parsed.y === 1 ? '' : 's'}`,
                        },
                    },
                    datalabels: { display: false },
                },
            },
        }));
    }

    // ---- Cumulative time ----
    charts.push(new Chart(document.getElementById('chart-area'), {
        type: 'line',
        data: {
            labels: data.area.labels,
            datasets: [{
                data: data.area.data,
                borderColor: LAVENDER,
                backgroundColor: 'rgba(163, 148, 189, 0.14)',
                fill: true,
                tension: 0.3,
                borderWidth: 2,
                pointRadius: data.area.labels.length <= 31 ? 2.5 : 0,
                pointBackgroundColor: LAVENDER,
                pointHoverRadius: 4,
            }],
        },
        options: {
            maintainAspectRatio: false,
            scales: { x: xAxis, y: { ...minAxis, beginAtZero: true } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (c) => ` ${fmtMin(data.bar.data[c.dataIndex] || 0)} this day · ${fmtMin(c.parsed.y)} total`,
                    },
                },
                datalabels: {
                    display: (c) => c.dataIndex === c.dataset.data.length - 1,
                    anchor: 'end', align: 'top', offset: 2,
                    color: '#8b7fa6', font: { size: 10, weight: '700' },
                    formatter: (v) => `Total ${fmtMin(v)}`,
                },
            },
        },
    }));

    // ---- Focus vs break totals ----
    const fbEl = document.getElementById('chart-focusbreak');
    if (fbEl) {
        charts.push(new Chart(fbEl, {
            type: 'bar',
            data: {
                labels: ['Focus', 'Breaks'],
                datasets: [{
                    data: [data.focus_break.focus, data.focus_break.breaks],
                    backgroundColor: [SAGE, '#cfc4dd'],
                    borderRadius: 8,
                    maxBarThickness: 90,
                }],
            },
            options: {
                maintainAspectRatio: false,
                scales: {
                    x: { ...axisBase, grid: { display: false } },
                    y: minAxis,
                },
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (c) => ` ${c.label}: ${fmtMin(c.parsed.y)}` } },
                    datalabels: {
                        display: (c) => c.dataset.data[c.dataIndex] > 0,
                        anchor: 'end', align: 'top', offset: 4,
                        color: C.tick, font: { size: 13, weight: '700' },
                        formatter: fmtMin,
                    },
                },
            },
        }));
    }

    // ---- Re-theme on dark/light toggle ----
    document.addEventListener('themechange', () => {
        C = themeColors();
        charts.forEach((chart) => {
            if (chart.options.scales) {
                chart.options.scales.x.ticks.color = C.tick;
                chart.options.scales.y.ticks.color = C.tick;
                if (chart.options.scales.y.grid) chart.options.scales.y.grid.color = C.grid;
            }
            if (chart.config.type === 'doughnut') {
                chart.data.datasets[0].borderColor = C.surface;
            }
            chart.update();
        });
    });
})();
