/**
 * X-Analytics 前端逻辑
 * 从 API 获取数据并渲染图表
 */

// API 基础路径
const API_BASE = '/analytics/api';

// ============================================
// 工具函数
// ============================================
async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API 请求失败: ${endpoint}`, error);
        return null;
    }
}

function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined) return '--';
    if (Math.abs(num) >= 100000000) {
        return (num / 100000000).toFixed(decimals) + '亿';
    } else if (Math.abs(num) >= 10000) {
        return (num / 10000).toFixed(decimals) + '万';
    }
    return num.toFixed(decimals);
}

// ============================================
// 恐慌贪婪指数
// ============================================
async function loadFearGreedIndex() {
    const data = await fetchAPI('/sentiment/fear-greed');
    const infoEl = document.getElementById('fear-greed-info');
    const chartEl = document.getElementById('fear-greed-gauge');

    if (!data || data.error) {
        infoEl.innerHTML = `<p class="error">数据加载失败</p>`;
        return;
    }

    const score = Math.round(data.score || 50);
    const status = data.status || '中性';

    // 渲染 ECharts 仪表盘
    const chart = echarts.init(chartEl);
    const option = {
        series: [{
            type: 'gauge',
            startAngle: 180,
            endAngle: 0,
            min: 0,
            max: 100,
            splitNumber: 5,
            progress: {
                show: true,
                width: 18
            },
            axisLine: {
                lineStyle: {
                    width: 18,
                    color: [
                        [0.2, '#333333'],
                        [0.4, '#555555'],
                        [0.6, '#777777'],
                        [0.8, '#999999'],
                        [1, '#cccccc']
                    ]
                }
            },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: {
                distance: 25,
                color: '#888888',
                fontSize: 12,
                formatter: function (value) {
                    if (value === 0) return '恐慌';
                    if (value === 50) return '中性';
                    if (value === 100) return '贪婪';
                    return '';
                }
            },
            pointer: {
                icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
                length: '60%',
                width: 10,
                itemStyle: {
                    color: '#ffffff'
                }
            },
            detail: {
                valueAnimation: true,
                formatter: '{value}',
                fontSize: 32,
                fontWeight: 'bold',
                color: '#ffffff',
                offsetCenter: [0, '40%']
            },
            data: [{ value: score }]
        }]
    };
    chart.setOption(option);

    // 渲染信息
    infoEl.innerHTML = `
        <div style="text-align: center;">
            <span class="status">${status}</span>
            <p class="label" style="margin-top: 12px;">
                RSI: ${data.rsi?.toFixed(1) || '--'} | 
                Bias: ${data.bias?.toFixed(2) || '--'}%
            </p>
        </div>
    `;

    // 监听窗口变化
    window.addEventListener('resize', () => chart.resize());
}

// ============================================
// 北向资金
// ============================================
async function loadNorthFlow() {
    const data = await fetchAPI('/sentiment/north-flow');
    const statsEl = document.getElementById('north-flow-stats');

    if (!data || data.error) {
        statsEl.innerHTML = `<p class="error">数据加载失败: ${data?.message || '未知错误'}</p>`;
        return;
    }

    const totalBuy = data.total_buy || 0;
    const totalSell = data.total_sell || 0;
    const netFlow = data.net_flow || 0;

    statsEl.innerHTML = `
        <div class="stat-item">
            <div class="stat-value ${netFlow >= 0 ? 'positive' : 'negative'}">
                ${netFlow >= 0 ? '+' : ''}${formatNumber(netFlow)}
            </div>
            <div class="stat-label">今日净流入</div>
        </div>
        <div class="stat-item">
            <div class="stat-value positive">${formatNumber(totalBuy)}</div>
            <div class="stat-label">买入额</div>
        </div>
        <div class="stat-item">
            <div class="stat-value negative">${formatNumber(totalSell)}</div>
            <div class="stat-label">卖出额</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">${data.sentiment || '--'}</div>
            <div class="stat-label">情绪判断</div>
        </div>
    `;
}

// ============================================
// 中国波指 QVIX
// ============================================
async function loadQVIX() {
    const data = await fetchAPI('/sentiment/qvix');
    const listEl = document.getElementById('qvix-list');

    if (!data || data.error) {
        listEl.innerHTML = `<p class="error">数据加载失败: ${data?.message || '未知错误'}</p>`;
        return;
    }

    // 渲染列表
    const indices = data.indices || [];
    if (indices.length === 0) {
        listEl.innerHTML = `<p class="loading">暂无数据</p>`;
        return;
    }

    listEl.innerHTML = indices.map(item => `
        <div class="qvix-item">
            <span class="qvix-name">${item.name || item.code}</span>
            <span class="qvix-value">${item.value?.toFixed(2) || '--'}</span>
        </div>
    `).join('');
}

// ============================================
// 初始化
// ============================================
async function init() {
    // 并行加载所有数据
    await Promise.all([
        loadFearGreedIndex(),
        loadNorthFlow(),
        loadQVIX()
    ]);

    // 更新时间
    const updateTimeEl = document.getElementById('update-time');
    updateTimeEl.textContent = `最后更新: ${new Date().toLocaleString('zh-CN')}`;
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
