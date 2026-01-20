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

// 2.6. Gold Silver Ratio (High Frequency)
async function loadGoldSilverRatio() {
    const el = document.getElementById('gold-silver-ratio');
    if (!el) return;

    const data = await fetchAPI('/commodity/gold-silver');

    if (!data || data.error) {
        el.innerHTML = '<div class="loading">暂无数据</div>';
        return;
    }

    const gold = data.gold;
    const silver = data.silver;
    const ratio = data.ratio;

    const goldChangeClass = formatters.colorClass(gold.change_pct);
    const silverChangeClass = formatters.colorClass(silver.change_pct);
    const goldSign = gold.change_pct >= 0 ? '+' : '';
    const silverSign = silver.change_pct >= 0 ? '+' : '';

    el.innerHTML = `
        <div class="gold-silver-item">
            <div class="item-label">🥇 黄金</div>
            <div class="item-price">$${gold.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            <span class="item-change ${goldChangeClass} bg-${gold.change_pct >= 0 ? 'up' : 'down'}-soft">${goldSign}${gold.change_pct.toFixed(2)}%</span>
        </div>
        <div class="gold-silver-item">
            <div class="item-label">🥈 白银</div>
            <div class="item-price">$${silver.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            <span class="item-change ${silverChangeClass} bg-${silver.change_pct >= 0 ? 'up' : 'down'}-soft">${silverSign}${silver.change_pct.toFixed(2)}%</span>
        </div>
        <div class="gold-silver-item ratio">
            <div class="item-label">📊 金银比</div>
            <div class="item-price">${ratio.current}</div>
            <div class="item-desc">${ratio.analysis?.comment || '--'}</div>
        </div>
    `;
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

// ============================================
// US Market & Metals Loading Logic
// ============================================

// 5. US Fear & Greed
async function loadUSFearGreed() {
    // Load CNN Index
    const cnnData = await fetchAPI('/us/fear-greed');
    const cnnContainer = document.getElementById('us-cnn-fear');

    if (cnnContainer) {
        if (!cnnData || cnnData.error) {
            cnnContainer.innerHTML = '<div class="placeholder"><p>暂无CNN数据</p></div>';
        } else {
            const score = cnnData.current_value || 50;
            const level = cnnData.current_level || '中性';
            const date = cnnData.date ? cnnData.date.substring(0, 10) : '--';

            cnnContainer.innerHTML = `
                <div class="fear-greed-display">
                    <div class="fg-score class-${getScoreClass(score)}">${score}</div>
                    <div class="fg-level">${level}</div>
                    <div class="fg-meta">
                        <span>日变动: ${formatters.percent(cnnData.change_1d || 0)}</span>
                        <span>更新: ${date}</span>
                    </div>
                </div>
            `;
        }
    }

    // Load Custom Index
    const customData = await fetchAPI('/us/fear-greed/custom');
    const customContainer = document.getElementById('us-custom-fear');

    if (customContainer) {
        if (!customData || customData.error) {
            customContainer.innerHTML = '<div class="placeholder"><p>暂无自定义数据</p></div>';
        } else {
            const score = customData.score || 50;
            const level = customData.level || '中性';

            // Build indicator badges
            let indicatorsHtml = '';
            if (customData.indicators) {
                const mapName = {
                    "vix": "VIX", "sp500_momentum": "S&P动量",
                    "market_breadth": "广度", "safe_haven": "避险"
                };
                for (const [key, val] of Object.entries(customData.indicators)) {
                    indicatorsHtml += `
                        <div class="fg-badge">
                            <span>${mapName[key] || key}</span>
                            <span class="${formatters.colorClass(val.score - 50)}">${Math.round(val.score)}</span>
                        </div>
                    `;
                }
            }

            customContainer.innerHTML = `
                <div class="fear-greed-display">
                    <div class="fg-score class-${getScoreClass(score)}">${score}</div>
                    <div class="fg-level">${level}</div>
                    <div class="fg-indicators">
                        ${indicatorsHtml}
                    </div>
                </div>
            `;
        }
    }
}

function getScoreClass(score) {
    if (score >= 75) return 'extreme-greed';
    if (score >= 55) return 'greed';
    if (score <= 25) return 'extreme-fear';
    if (score <= 45) return 'fear';
    return 'neutral';
}

// 6. US Market Heat (Sectors)
async function loadUSMarketHeat() {
    const el = document.getElementById('market-us-heat');
    if (!el) return;

    const data = await fetchAPI('/us/market-heat');
    if (!data || data.length === 0) {
        el.innerHTML = '<div class="placeholder"><p>暂无数据</p></div>';
        return;
    }

    // Render as a grid of blocks
    el.innerHTML = data.map(item => {
        const change = item.change_pct;
        // Determine background intensity based on change magnitude
        const intensity = Math.min(Math.abs(change) * 10, 50) + 10; // example scaling
        const colorVar = change >= 0 ? `rgba(34, 197, 94, ${intensity / 100})` : `rgba(239, 68, 68, ${intensity / 100})`;

        return `
            <div class="heat-block" style="background-color: ${colorVar}">
                <div class="heat-name">${item.name}</div>
                <div class="heat-val">${formatters.percent(change)}</div>
            </div>
        `;
    }).join('');
}

// 7. US Bond Yields
async function loadUSBondYields() {
    const el = document.getElementById('us-treasury');
    if (!el) return;

    const data = await fetchAPI('/us/bond-yields');
    if (!data || data.length === 0) {
        el.innerHTML = '<div class="placeholder"><p>暂无数据</p></div>';
        return;
    }

    el.innerHTML = data.map(item => {
        let valClass = '';
        if (item.is_spread) {
            valClass = item.value < 0 ? 'text-down' : 'text-up';
        }

        return `
            <div class="bond-item">
                <span class="bond-name">${item.name}</span>
                <span class="bond-val ${valClass}">${item.value}${item.suffix || ''}</span>
            </div>
        `;
    }).join('');
}

// 8. Metal Spot Prices
async function loadMetalSpotPrices() {
    const el = document.getElementById('metal-prices');
    if (!el) return;

    const data = await fetchAPI('/metals/spot-prices');
    if (!data || data.length === 0) {
        el.innerHTML = '<div class="placeholder"><p>暂无数据</p></div>';
        return;
    }

    el.innerHTML = `
        <table class="simple-table">
            <thead>
                <tr>
                    <th>名称</th>
                    <th>价格</th>
                    <th>涨跌幅</th>
                </tr>
            </thead>
            <tbody>
                ${data.map(item => `
                    <tr>
                        <td>${item.name}</td>
                        <td>${item.price}</td>
                        <td class="${formatters.colorClass(item.change_pct)}">${formatters.percent(item.change_pct)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// ============================================
// Initialization & Loop
// ============================================
function updateTime() {
    const el = document.getElementById('update-time');
    if (el) el.innerHTML = `${lucideIcon('clock', 'footer-icon')} Last Updated: <span class="font-mono">${new Date().toLocaleTimeString('en-US', { hour12: false })}</span>`;

    // Also update footer time
    const footerEl = document.getElementById('footer-update-time');
    if (footerEl) footerEl.innerText = new Date().toLocaleString('zh-CN');

    // Refresh icons for dynamic content if needed
    if (window.lucide) lucide.createIcons();
}

async function init() {
    updateTime();

    // Initial Load
    await loadFearGreedIndex();
    await loadGoldSilverRatio();
    await loadMarketOverview();

    // New Loaders
    // We run these without awaiting them to block the initial UI less, or await if we want strict order
    // But since they are independent, parallel is fine.
    loadUSFearGreed();
    loadUSMarketHeat();
    loadUSBondYields();
    loadMetalSpotPrices();

    Promise.all([
        loadSectorTop(),
        loadSectorBottom()
    ]).then(() => {
        if (window.lucide) lucide.createIcons();
    });

    // Setup Tab Switching for US Fear & Greed Cards
    setupCardTabs();
    // Setup Main Tabs
    setupMainTabs();

    // Refresh Strategy
    const MINUTE = 60 * 1000;
    const HOUR = 60 * MINUTE;

    setInterval(updateTime, MINUTE);

    // 5-min Group
    setInterval(async () => {
        await loadFearGreedIndex();
        await loadGoldSilverRatio();
        await loadMetalSpotPrices();
    }, 5 * MINUTE);

    // 30-min Group (US Market)
    setInterval(async () => {
        await loadUSFearGreed();
        await loadUSMarketHeat();
        await loadUSBondYields();
    }, 30 * MINUTE);

    // 1-hour Group
    setInterval(async () => {
        await loadMarketOverview();
        await loadSectorTop();
        await loadSectorBottom();
    }, 1 * HOUR);
}

function setupCardTabs() {
    const tabButtons = document.querySelectorAll('.card-tab');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Find parent card header to limit scope
            const header = btn.closest('.card-header');
            if (!header) return;

            // Siblings buttons
            header.querySelectorAll('.card-tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Content switching
            const targetId = btn.getAttribute('data-target');
            const cardBody = header.nextElementSibling;
            if (cardBody && targetId) {
                // Hide all containers in this body
                const containers = cardBody.children;
                for (let i = 0; i < containers.length; i++) {
                    containers[i].classList.remove('active');
                    containers[i].style.display = 'none'; // Ensure hidden
                }

                // Show target
                const target = document.getElementById(targetId);
                if (target) {
                    target.classList.add('active');
                    target.style.display = 'block';
                }
            }
        });
    });
}

function setupMainTabs() {
    const tabs = document.querySelectorAll('.tab-navigation .tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const targetId = tab.getAttribute('data-tab');
            document.querySelectorAll('.tab-content').forEach(c => {
                c.classList.remove('active');
                if (c.id === targetId) c.classList.add('active');
            });
        });
    });
}

document.addEventListener('DOMContentLoaded', init);
