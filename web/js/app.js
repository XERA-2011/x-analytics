/**
 * x-analytics Dashboard Controller
 * Handles data fetching, processing, and UI rendering
 * Based on UI UX Pro Max Refactoring
 */

// API Configuration
const API_BASE = '/analytics/api';

// ============================================
// Utilities
// ============================================
const formatters = {
    number: (num, decimals = 2) => {
        if (num === null || num === undefined) return '--';
        if (Math.abs(num) >= 100000000) return (num / 100000000).toFixed(decimals) + '亿';
        if (Math.abs(num) >= 10000) return (num / 10000).toFixed(decimals) + '万';
        return num.toFixed(decimals);
    },
    percent: (num) => {
        if (num === null || num === undefined) return '--';
        return (num > 0 ? '+' : '') + num.toFixed(2) + '%';
    },
    colorClass: (num) => {
        if (num > 0) return 'text-up';
        if (num < 0) return 'text-down';
        return 'text-tertiary'; // Changed from neutral to new CSS var
    },
    iconClass: (num) => {
        return num > 0 ? 'icon-up' : (num < 0 ? 'icon-down' : '');
    }
};

/**
 * Enhanced Fetch Wrapper with Error Handling
 */
async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        return null;
    }
}

/**
 * Creates a Lucide Icon string
 */
function lucideIcon(name, classes = "") {
    // Note: lucide.createIcons() must be called after insertion
    return `<i data-lucide="${name}" class="${classes}"></i>`;
}

// ============================================
// Renderers
// ============================================

// 1. Fear & Greed Index (High Frequency)
async function loadFearGreedIndex() {
    const data = await fetchAPI('/sentiment/fear-greed');
    const chartEl = document.getElementById('fear-greed-gauge');
    const infoEl = document.getElementById('fear-greed-info');

    if (!data || data.error) {
        infoEl.innerHTML = '<span class="text-tertiary">暂无数据</span>';
        if (chartEl) chartEl.innerHTML = '';
        return;
    }

    const score = Math.round(data.score || 50);
    const chart = echarts.init(chartEl);

    // Dynamic Gradient based on theme
    const axisColors = [
        [0.2, '#22c55e'], // Green (Fear/Opportunity)
        [0.4, '#86efac'],
        [0.6, '#94a3b8'], // Slate (Neutral)
        [0.8, '#fca5a5'],
        [1, '#ef4444']    // Red (Greed/Risk)
    ];

    const option = {
        series: [{
            type: 'gauge',
            startAngle: 180,
            endAngle: 0,
            min: 0,
            max: 100,
            radius: '100%',     // Reduced radius from 110% to 100%
            center: ['50%', '70%'], // Moved center up from 75% to 70%
            splitNumber: 5,
            itemStyle: { color: '#f8fafc' },
            progress: { show: true, width: 18 },
            pointer: {
                icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
                length: '60%',
                width: 6,
                offsetCenter: [0, -35],
                itemStyle: { color: 'auto' }
            },
            axisLine: {
                lineStyle: { width: 18, color: axisColors }
            },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: { show: false },
            title: { show: false },
            detail: {
                valueAnimation: true,
                fontSize: 56,
                fontWeight: 'bold',
                fontFamily: 'Fira Code',
                color: '#fff',
                offsetCenter: [0, -10], // Moved value slightly higher
                formatter: '{value}'
            },
            data: [{ value: score }]
        }]
    };
    chart.setOption(option);

    // Update Info Overlay
    let status = '中性';
    if (score > 80) status = '极度贪婪';
    else if (score > 60) status = '贪婪';
    else if (score < 20) status = '极度恐慌';
    else if (score < 40) status = '恐慌';

    infoEl.innerHTML = `
        <div style="font-size: 1.25em; font-weight: 600; margin-bottom: 8px; margin-top: 10px; text-shadow: 0 0 10px rgba(0,0,0,0.5);">${status}</div>
        <div style="font-size: 0.9em; color: var(--text-secondary); background: rgba(0,0,0,0.3); padding: 4px 12px; border-radius: 99px; display: inline-block;">
            RSI: <span class="font-mono">${data.rsi?.toFixed(1) || '--'}</span> <span style="opacity:0.3; margin:0 4px">|</span> Bias: <span class="font-mono">${data.bias?.toFixed(1) || '--'}%</span>
        </div>
    `;

    window.addEventListener('resize', () => chart.resize());
}

// 2. Core Indices (High Frequency)
async function loadIndexCompare() {
    const el = document.getElementById('index-list');
    const data = await fetchAPI('/index/compare');

    if (!data || data.length === 0) {
        el.innerHTML = '<div class="loading">暂无数据</div>';
        return;
    }

    el.innerHTML = data.map(item => {
        let change = parseFloat(item['1日涨跌'].replace('%', ''));
        let changeStr = item['1日涨跌'];
        const colorClass = formatters.colorClass(change);

        // Add trend icon
        // const trendIcon = change > 0 ? "trending-up" : (change < 0 ? "trending-down" : "minus");

        return `
        <div class="list-item index-item">
            <div class="item-name">${item['指数名称']}</div>
            <div class="index-value-group">
                <span class="item-value font-mono">${item['最新点位']}</span>
                <span class="item-change font-mono ${colorClass} bg-${change > 0 ? 'up' : 'down'}-soft">${changeStr}</span>
            </div>
        </div>
        `;
    }).join('');

    // Lucide icons are not needed inside list items for performance, keeping it clean
}

// 3. Market Overview (Medium Frequency)
async function loadMarketOverview() {
    const el = document.getElementById('market-overview');
    const data = await fetchAPI('/market/overview');

    if (!data || !data.stats) {
        el.innerHTML = '<div class="loading">暂无数据</div>';
        return;
    }

    const { up, down } = data.stats;
    const total = up + down;
    const upRatio = total > 0 ? (up / total * 100).toFixed(0) : 0;

    el.innerHTML = `
        <div class="stat-box up">
            <div class="stat-num text-up">${up}</div>
            <div class="stat-desc">上涨家数 (${upRatio}%)</div>
        </div>
        <div class="stat-box down">
            <div class="stat-num text-down">${down}</div>
            <div class="stat-desc">下跌家数</div>
        </div>
        <div class="stat-box" style="grid-column: span 2;">
            <div class="stat-num font-mono" style="font-size: 1.5rem; color: var(--text-primary);">
                ${data.volume_str || '--'}
            </div>
            <div class="stat-desc">两市总成交额</div>
        </div>
    `;
}

// 4. Sector Monitors (Medium Frequency)
async function loadSectorList(endpoint, elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const data = await fetchAPI(endpoint);

    if (!data || data.length === 0) {
        el.innerHTML = '<div class="loading">暂无数据</div>';
        return;
    }

    el.innerHTML = data.map(item => {
        const change = item['涨跌幅'];
        // const stockChange = item['领涨股票-涨跌幅'];

        return `
        <div class="list-item">
            <div class="item-info">
                <span class="item-name">${item['板块名称']}</span>
            </div>
            <div class="item-value font-mono ${formatters.colorClass(change)}">
                ${formatters.percent(change)}
            </div>
        </div>
        `;
    }).join('');
}

async function loadSectorTop() { await loadSectorList('/market/sector-top?n=5', 'sector-list'); }
async function loadSectorBottom() { await loadSectorList('/market/sector-bottom?n=5', 'sector-list-bottom'); }

// 5. Fund Rankings (Low Frequency)
async function loadFundTop() {
    const el = document.getElementById('fund-list');
    const data = await fetchAPI('/fund/top?n=12'); // Increased to 12

    if (!data || data.length === 0) {
        el.innerHTML = '<div class="loading">暂无数据</div>';
        return;
    }

    el.innerHTML = data.map(item => `
        <div class="fund-card">
            <div class="fund-info" style="overflow: hidden; max-width: 70%;">
                <h4 style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    ${item['基金简称']}
                </h4>
                <span class="font-mono">${item['基金代码']}</span>
            </div>
            <div class="fund-rate text-up font-mono">
                +${item['日增长率']}%
            </div>
        </div>
    `).join('');
}

// ============================================
// Initialization & Loop
// ============================================
function updateTime() {
    const el = document.getElementById('update-time');
    if (el) el.innerHTML = `${lucideIcon('clock', 'footer-icon')} Last Updated: <span class="font-mono">${new Date().toLocaleTimeString('en-US', { hour12: false })}</span>`;

    // Refresh icons for dynamic content if needed
    if (window.lucide) lucide.createIcons();
}

async function init() {
    updateTime();

    // Initial Load - Sequential to avoid race conditions affecting layout
    await loadFearGreedIndex();
    await loadIndexCompare();
    await loadMarketOverview();

    // Parallel Load for lower priority
    Promise.all([
        loadSectorTop(),
        loadSectorBottom(),
        loadFundTop()
    ]).then(() => {
        // Refresh icons once everything is loaded
        if (window.lucide) lucide.createIcons();
    });

    // Refresh Strategy
    const MINUTE = 60 * 1000;
    const HOUR = 60 * MINUTE;

    setInterval(updateTime, MINUTE);

    // 5-min Group
    setInterval(async () => {
        await loadFearGreedIndex();
        await loadIndexCompare();
    }, 5 * MINUTE);

    // 1-hour Group
    setInterval(async () => {
        await loadMarketOverview();
        await loadSectorTop();
        await loadSectorBottom();
    }, 1 * HOUR);

    // 12-hour Group
    setInterval(() => {
        loadFundTop();
    }, 12 * HOUR);
}

document.addEventListener('DOMContentLoaded', init);
