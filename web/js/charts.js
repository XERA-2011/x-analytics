// 图表组件模块

class Charts {
    constructor() {
        this.charts = new Map();
        this.theme = this.getTheme();
    }

    // 获取主题配置
    getTheme() {
        // Bloomberg Style: High Contrast, no dark mode detection
        return {
            backgroundColor: 'transparent',
            textStyle: {
                color: '#000000',
                fontFamily: 'Helvetica Neue, Helvetica, Arial, sans-serif'
            },
            grid: {
                borderColor: '#e6e6e6',
                containLabel: true,
                left: '2%',
                right: '2%',
                bottom: '5%'
            }
        };
    }

    // 颜色插值算法（用于计算精确渐变过渡色）
    _interpolateColor(color1, color2, factor) {
        const c1 = parseInt(color1.slice(1), 16);
        const c2 = parseInt(color2.slice(1), 16);
        const r1 = (c1 >> 16) & 255, g1 = (c1 >> 8) & 255, b1 = c1 & 255;
        const r2 = (c2 >> 16) & 255, g2 = (c2 >> 8) & 255, b2 = c2 & 255;
        const r = Math.round(r1 + factor * (r2 - r1));
        const g = Math.round(g1 + factor * (g2 - g1));
        const b = Math.round(b1 + factor * (b2 - b1));
        return `rgb(${r}, ${g}, ${b})`;
    }

    // 根据百分比从 stops 获取精确颜色
    _getGradientAt(pct, stops) {
        pct = Math.max(0, Math.min(1, pct));
        for (let i = 0; i < stops.length - 1; i++) {
            if (pct >= stops[i].pct && pct <= stops[i+1].pct) {
                const factor = (pct - stops[i].pct) / (stops[i+1].pct - stops[i].pct);
                return this._interpolateColor(stops[i].color, stops[i+1].color, factor);
            }
        }
        return stops[stops.length - 1].color;
    }

    // 创建恐慌贪婪指数仪表盘 (风格 1: 外圈渐变弧线 + 内圈渐变刻度 + 箭头游标 + 居中分值)
    createFearGreedGauge(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) return null;

        // 清理现有图表 (兼容原 ECharts 实例清理)
        if (this.charts.has(containerId)) {
            const old = this.charts.get(containerId);
            if (old && typeof old.dispose === 'function') {
                try { old.dispose(); } catch (e) {}
            }
            this.charts.delete(containerId);
        }

        const score = data.score ?? data.current_value;
        if (score == null) {
            container.innerHTML = '<div class="loading error">数据不可用</div>';
            return null;
        }

        const isUS = containerId.includes('western') || data?.meta?.market === 'US' || data?.market === 'US';
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

        // 风格 1：A股标准色谱 (蓝 -> 青 -> 灰 -> 橙 -> 红)
        const STOPS_CN = [
            { pct: 0.0, color: '#2563eb' },
            { pct: 0.25, color: '#06b6d4' },
            { pct: 0.50, color: '#64748b' },
            { pct: 0.75, color: '#f59e0b' },
            { pct: 1.0, color: '#ef4444' }
        ];

        // 美股标准色谱 (CNN Fear & Greed: 红 -> 橙 -> 黄 -> 青 -> 绿)
        const STOPS_US = [
            { pct: 0.0, color: '#ef4444' },
            { pct: 0.25, color: '#f97316' },
            { pct: 0.50, color: '#eab308' },
            { pct: 0.75, color: '#06b6d4' },
            { pct: 1.0, color: '#10b981' }
        ];

        const stops = isUS ? STOPS_US : STOPS_CN;
        const pct = Math.max(0, Math.min(100, score)) / 100;
        const currentColor = this._getGradientAt(pct, stops);

        // 同步父容器中的情绪等级文字颜色
        const parent = container.closest('.fg-container') || container.parentElement;
        if (parent) {
            const levelEl = parent.querySelector('.fg-level');
            if (levelEl) {
                levelEl.style.color = currentColor;
            }
        }

        const safeId = containerId.replace(/[^a-zA-Z0-9_-]/g, '');
        const gradId = `fg-grad-${safeId}`;
        const shadowId = `fg-shadow-${safeId}`;

        // 计算三角指示箭头顶点坐标 (精确指向刻度内圈)
        const angleDeg = 180 - pct * 180;
        const angleRad = (angleDeg * Math.PI) / 180;
        const cx = 190, cy = 175;
        const rTip = 96, rBase = 76, halfSpread = 0.085;
        const tipX = (cx + rTip * Math.cos(angleRad)).toFixed(1);
        const tipY = (cy - rTip * Math.sin(angleRad)).toFixed(1);
        const b1X = (cx + rBase * Math.cos(angleRad - halfSpread)).toFixed(1);
        const b1Y = (cy - rBase * Math.sin(angleRad - halfSpread)).toFixed(1);
        const b2X = (cx + rBase * Math.cos(angleRad + halfSpread)).toFixed(1);
        const b2Y = (cy - rBase * Math.sin(angleRad + halfSpread)).toFixed(1);

        // 生成 33 条放射状同心刻度线
        let ticksHtml = '';
        const outerR = 116;
        const totalTicks = 32;
        for (let i = 0; i <= totalTicks; i++) {
            const p = i / totalTicks;
            const aRad = ((180 - p * 180) * Math.PI) / 180;
            const isMajor = (i % 8 === 0);
            const isMedium = (i % 4 === 0 && !isMajor);
            const len = isMajor ? 11 : (isMedium ? 7 : 4.5);
            const strokeWidth = isMajor ? 2.2 : (isMedium ? 1.4 : 1.0);
            const innerR = outerR - len;
            const x1 = (cx + outerR * Math.cos(aRad)).toFixed(1);
            const y1 = (cy - outerR * Math.sin(aRad)).toFixed(1);
            const x2 = (cx + innerR * Math.cos(aRad)).toFixed(1);
            const y2 = (cy - innerR * Math.sin(aRad)).toFixed(1);
            const c = this._getGradientAt(p, stops);
            ticksHtml += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="${strokeWidth}" stroke-linecap="round" opacity="${isMajor ? 1 : 0.85}" />`;
        }

        // 外围等级文本颜色 (根据 CN/US 区分)
        const labelColors = isUS 
            ? ['#ef4444', '#f97316', isDark ? '#facc15' : '#eab308', '#06b6d4', '#10b981']
            : ['#2563eb', '#0284c7', isDark ? '#94a3b8' : '#64748b', '#f59e0b', '#ef4444'];

        const gradStops = stops.map(s => `<stop offset="${(s.pct * 100).toFixed(0)}%" stop-color="${s.color}" />`).join('');

        container.innerHTML = `
            <svg viewBox="0 0 380 185" class="fg-custom-gauge" style="width:100%;height:auto;display:block;overflow:visible;">
                <defs>
                    <linearGradient id="${gradId}" x1="0%" y1="100%" x2="100%" y2="100%">
                        ${gradStops}
                    </linearGradient>
                    <filter id="${shadowId}" x="-20%" y="-20%" width="140%" height="140%">
                        <feDropShadow dx="0" dy="1.5" stdDeviation="1.5" flood-opacity="${isDark ? 0.4 : 0.2}" />
                    </filter>
                </defs>
                <!-- 外层渐变主弧线 -->
                <path d="M 65 175 A 125 125 0 0 1 315 175" fill="none" stroke="url(#${gradId})" stroke-width="4.5" stroke-linecap="round" />
                <!-- 内层放射刻度 -->
                <g>${ticksHtml}</g>
                <!-- 外围等级标注 -->
                <text x="54" y="180" font-size="10" font-weight="600" fill="${labelColors[0]}" text-anchor="end">极度恐慌</text>
                <text x="86" y="76" font-size="10" font-weight="600" fill="${labelColors[1]}" text-anchor="middle">恐慌</text>
                <text x="190" y="32" font-size="10.5" font-weight="600" fill="${labelColors[2]}" text-anchor="middle">中性</text>
                <text x="294" y="76" font-size="10" font-weight="600" fill="${labelColors[3]}" text-anchor="middle">贪婪</text>
                <text x="326" y="180" font-size="10" font-weight="600" fill="${labelColors[4]}" text-anchor="start">极度贪婪</text>
                <!-- 三角指示游标 -->
                <polygon points="${tipX},${tipY} ${b1X},${b1Y} ${b2X},${b2Y}" fill="${currentColor}" filter="url(#${shadowId})" />
                <!-- 中心数值 -->
                <text x="190" y="152" font-size="38" font-weight="800" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" fill="${currentColor}" text-anchor="middle">${Math.round(score)}</text>
            </svg>
        `;

        const instance = {
            resize: () => {},
            dispose: () => {
                container.innerHTML = '';
            }
        };

        this.charts.set(containerId, instance);
        return instance;
    }

    // 创建收益率曲线图
    createYieldCurve(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) return null;

        if (this.charts.has(containerId)) {
            this.charts.get(containerId).dispose();
        }

        const chart = echarts.init(container);

        const periods = Object.keys(data.yield_curve || {});
        const yields = Object.values(data.yield_curve || {});

        const option = {
            ...this.theme,
            tooltip: {
                trigger: 'axis',
                formatter: function (params) {
                    const point = params[0];
                    return `${point.name}: ${point.value}%`;
                }
            },
            xAxis: {
                type: 'category',
                data: periods,
                axisLabel: {
                    color: this.theme.textStyle.color,
                    interval: 0, // Show all labels
                    rotate: window.innerWidth < 768 ? 90 : 0, // Vertical on mobile
                    fontSize: window.innerWidth < 768 ? 9 : 12,
                    margin: 8
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    formatter: '{value}%',
                    color: this.theme.textStyle.color,
                    fontSize: 10
                },
                splitLine: {
                    show: true,
                    lineStyle: {
                        color: '#f0f0f0'
                    }
                }
            },
            grid: {
                left: '10%',
                right: '5%',
                bottom: window.innerWidth < 768 ? '25%' : '10%', // More space for vertical labels
                top: '10%'
            },
            series: [{
                data: yields,
                type: 'line',
                smooth: true,
                lineStyle: {
                    color: '#000000',
                    width: 2
                },
                itemStyle: {
                    color: '#000000'
                }
            }]
        };

        chart.setOption(option);
        this.charts.set(containerId, chart);

        window.addEventListener('resize', () => {
            chart.resize();
        });

        return chart;
    }

    // 创建金银比历史走势图
    createGoldSilverChart(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) return null;

        if (this.charts.has(containerId)) {
            this.charts.get(containerId).dispose();
        }

        const chart = echarts.init(container);

        const history = data.history || [];
        const dates = history.map(item => item.date);
        const ratios = history.map(item => item.ratio);

        const option = {
            ...this.theme,
            tooltip: {
                trigger: 'axis',
                formatter: function (params) {
                    const point = params[0];
                    return `${point.name}<br/>金银比: ${point.value}`;
                }
            },
            xAxis: {
                type: 'category',
                data: dates,
                axisLabel: {
                    color: this.theme.textStyle.color,
                    formatter: function (value) {
                        return value.split('-').slice(1).join('/');
                    }
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    color: this.theme.textStyle.color
                }
            },
            series: [{
                data: ratios,
                type: 'line',
                smooth: true,
                lineStyle: {
                    color: '#000000',
                    width: 2
                },
                itemStyle: {
                    color: '#000000'
                }
            }]
        };

        chart.setOption(option);
        this.charts.set(containerId, chart);

        window.addEventListener('resize', () => {
            chart.resize();
        });

        return chart;
    }

    // 销毁所有图表
    dispose() {
        this.charts.forEach(chart => {
            chart.dispose();
        });
        this.charts.clear();
    }

    // 响应式处理
    resize() {
        this.charts.forEach(chart => {
            if (chart && typeof chart.resize === 'function') {
                chart.resize();
            }
        });
    }
    // 渲染 Treemap (实例方法)
    renderTreemap(containerId, data) {
        const dom = document.getElementById(containerId);
        if (!dom) return;

        // Ensure container has height
        if (dom.clientHeight === 0) {
            dom.style.height = '400px';
        }

        // 销毁旧实例 (如果有)
        const oldInstance = echarts.getInstanceByDom(dom);
        if (oldInstance) {
            oldInstance.dispose();
        }
        if (this.charts.has(containerId)) {
            this.charts.get(containerId).dispose();
            this.charts.delete(containerId);
        }

        const chart = echarts.init(dom, "dark", {
            width: dom.clientWidth || undefined,
            height: dom.clientHeight || undefined
        });

        const getSentiment = (c, t) => {
            let analysis = "中性";
            let analysisColor = "#9ca3af";
            const absC = Math.abs(c);

            if (absC < 0.8) {
                analysis = "横盘震荡";
                analysisColor = "#9ca3af";
            } else if (c > 0) {
                if (t === null || t === undefined) {
                    if (c > 8) { analysis = "逼空拉升"; analysisColor = "#dc2626"; }
                    else if (c > 4) { analysis = "放量上攻"; analysisColor = "#ef4444"; }
                    else { analysis = "温和上涨"; analysisColor = "#ef4444"; }
                } else {
                    if (c > 8) { analysis = t > 2 ? "极度超买" : "逼空拉升"; analysisColor = "#dc2626"; }
                    else if (t > 5 && c > 4) { analysis = "严重超买"; analysisColor = "#dc2626"; }
                    else if (t > 3 || c > 4) { analysis = "放量上攻"; analysisColor = "#ef4444"; }
                    else if (t < 1.2 && c < 2) { analysis = "缩量上涨"; analysisColor = "#f59e0b"; }
                    else { analysis = "温和上涨"; analysisColor = "#ef4444"; }
                }
            } else {
                if (t === null || t === undefined) {
                    if (c < -8) { analysis = "恐慌抛售"; analysisColor = "#16a34a"; }
                    else if (c < -4) { analysis = "放量杀跌"; analysisColor = "#16a34a"; }
                    else { analysis = "弱势调整"; analysisColor = "#22c55e"; }
                } else {
                    if (c < -8) { analysis = t > 2 ? "恐慌抛售" : "闷杀出局"; analysisColor = "#16a34a"; }
                    else if (t > 5 && c < -4) { analysis = "恐慌抛售"; analysisColor = "#16a34a"; }
                    else if (t > 3 || c < -4) { analysis = "放量杀跌"; analysisColor = "#16a34a"; }
                    else if (t < 1.2 && c > -2) { analysis = "无量下跌"; analysisColor = "#10b981"; }
                    else { analysis = "弱势调整"; analysisColor = "#22c55e"; }
                }
            }
            return { analysis, analysisColor };
        };

        const treeData = data.map(item => {
            const change = Number.isFinite(Number(item.change_pct)) ? Number(item.change_pct) : 0;
            const hasTurnover = item.turnover !== null && item.turnover !== undefined;
            const turnover = hasTurnover && Number.isFinite(Number(item.turnover)) ? Number(item.turnover) : null;
            const sentiment = getSentiment(change, turnover);

            let leadingStr = item.leading_stock;
            let laggingStr = item.lagging_stock;
            let topCapStockStr = '';

            // Fetch the individual stock's percentage change from the children array if possible
            if (Array.isArray(item.children)) {
                if (item.children.length > 0) {
                    const sortedByCap = [...item.children].sort((a, b) => (b.value || 0) - (a.value || 0));
                    const topStock = sortedByCap[0];
                    if (topStock) {
                        const c = Number.isFinite(Number(topStock.change_pct)) ? Number(topStock.change_pct) : 0;
                        topCapStockStr = `${topStock.name} ${c >= 0 ? '+' : ''}${c.toFixed(2)}%`;
                    }
                }
                if (leadingStr && leadingStr !== 'undefined') {
                    const leadStock = item.children.find(s => s.name === leadingStr);
                    if (leadStock) {
                        const c = Number.isFinite(Number(leadStock.change_pct)) ? Number(leadStock.change_pct) : 0;
                        leadingStr = `${leadingStr} ${c >= 0 ? '+' : ''}${c.toFixed(2)}%`;
                    }
                }
                if (laggingStr && laggingStr !== 'undefined') {
                    const lagStock = item.children.find(s => s.name === laggingStr);
                    if (lagStock) {
                        const c = Number.isFinite(Number(lagStock.change_pct)) ? Number(lagStock.change_pct) : 0;
                        laggingStr = `${laggingStr} ${c >= 0 ? '+' : ''}${c.toFixed(2)}%`;
                    }
                }
            }

            // 统一风格：采用标准的 Tailwind 色阶（500 级匹配文字，向下到 900 级），保持色彩高对比与纯正饱和度（防发白发灰）
            let bgColor;
            if (change >= 3.0) { bgColor = '#ef4444'; }       // Red 500 (同文字大红)
            else if (change >= 2.0) { bgColor = '#dc2626'; }  // Red 600
            else if (change >= 1.0) { bgColor = '#b91c1c'; }  // Red 700
            else if (change > 0) { bgColor = '#7f1d1d'; }     // Red 900 (极深红)
            else if (change === 0) { bgColor = '#27272a'; }   // Zinc 800 (深中性暗灰)
            else if (change > -1.0) { bgColor = '#14532d'; }  // Green 900 (极深绿)
            else if (change > -2.0) { bgColor = '#15803d'; }  // Green 700
            else if (change > -3.0) { bgColor = '#16a34a'; }  // Green 600
            else { bgColor = '#22c55e'; }                     // Green 500 (同文字大绿)

            return {
                name: item.name,
                code: item.code,
                value: item.value || 1, // Fallback to 1 to ensure it renders
                change_pct: change,
                top_cap_stock: topCapStockStr,
                leading_stock: leadingStr,
                lagging_stock: laggingStr,
                turnover: turnover,
                amount: item.amount,
                analysis: sentiment.analysis,
                analysisColor: sentiment.analysisColor,
                itemStyle: {
                    color: bgColor
                }
            };
        });

        const option = {
            backgroundColor: "transparent",
            toolbox: {
                show: true,
                showTitle: false, // 禁用默认的 SVG 文本 label，防止与图表文字重叠
                tooltip: { // 启用基于 DOM 的悬浮提示
                    show: true,
                    backgroundColor: 'rgba(30, 30, 30, 0.95)',
                    textStyle: { color: '#fff', fontSize: 12 },
                    padding: [4, 8],
                    borderWidth: 1,
                    borderColor: '#404040',
                    formatter: function(param) {
                        return param.title; // 显示 feature.title
                    }
                },
                orient: 'vertical',
                left: 'right',
                top: 'top',
                feature: {
                    myShare: {
                        show: true,
                        title: '截图分享',
                        icon: 'path://M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z',
                        onclick: function () {
                            const dataURL = chart.getDataURL({
                                type: 'png',
                                pixelRatio: 2,
                                backgroundColor: '#121212',
                                excludeComponents: ['toolbox']
                            });
                            if (window.utils && utils.showShareModal) {
                                utils.showShareModal(dataURL, '行业板块热力图');
                            }
                        }
                    }
                },
                iconStyle: {
                    borderColor: '#9ca3af'
                }
            },
            tooltip: {
                trigger: 'item',
                formatter: function (info) {
                    const d = info.data;
                    if (!d || !d.name) {
                        return '';
                    }
                    const rawChange = d.change_pct !== undefined ? d.change_pct : 0;
                    const change = Number.isFinite(Number(rawChange)) ? Number(rawChange) : 0;
                    const color = change >= 0 ? "#ef4444" : "#22c55e";
                    let capStr = '--';
                    if (d.value && d.value !== 1) {
                        capStr = (d.value / 100000000).toFixed(0);
                    }

                    let trailingRows = '';
                    if (d.top_cap_stock) {
                        trailingRows += `
                            <tr style="line-height: 1.6;">
                                <td style="color: #9ca3af; padding-right: 12px;">龙头</td>
                                <td style="text-align: right; color: #e5e7eb; white-space: nowrap;">${d.top_cap_stock}</td>
                            </tr>
                        `;
                    }
                    if (d.leading_stock && d.leading_stock !== 'undefined') {
                        trailingRows += `
                            <tr style="line-height: 1.6;">
                                <td style="color: #9ca3af; padding-right: 12px;">领涨</td>
                                <td style="text-align: right; color: #e5e7eb; white-space: nowrap;">${d.leading_stock}</td>
                            </tr>
                        `;
                    }
                    if (d.lagging_stock && d.lagging_stock !== 'undefined') {
                        trailingRows += `
                            <tr style="line-height: 1.6;">
                                <td style="color: #9ca3af; padding-right: 12px;">领跌</td>
                                <td style="text-align: right; color: #e5e7eb; white-space: nowrap;">${d.lagging_stock}</td>
                            </tr>
                        `;
                    }

                    return `
                        <div style="min-width: 140px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px solid #404040;">
                                <span style="font-weight: 700; font-size: 14px; color: #fff;">${d.name}</span>
                                <span style="font-weight: 700; font-family: monospace; font-size: 14px; color:${color}">${change >= 0 ? '+' : ''}${change.toFixed(2)}%</span>
                            </div>
                            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                                <tr style="line-height: 1.6;">
                                    <td style="color: #9ca3af; padding-right: 12px;">情绪</td>
                                    <td style="text-align: right; font-weight: bold; color: ${d.analysisColor};">${d.analysis}</td>
                                </tr>
                                <tr style="line-height: 1.6;">
                                    <td style="color: #9ca3af; padding-right: 12px;">市值</td>
                                    <td style="text-align: right; font-family: monospace; color: #e5e7eb;">${capStr}亿</td>
                                </tr>
                                <tr style="line-height: 1.6;">
                                    <td style="color: #9ca3af; padding-right: 12px;">换手</td>
                                    <td style="text-align: right; font-family: monospace; color: #e5e7eb;">${d.turnover !== null && d.turnover !== undefined ? d.turnover + '%' : '--'}</td>
                                </tr>
                                ${trailingRows}
                            </table>
                        </div>
                    `;
                },
                backgroundColor: 'rgba(23, 23, 23, 0.95)',
                borderColor: '#404040',
                borderWidth: 1,
                padding: [8, 10],
                textStyle: { color: '#fff' },
                extraCssText: 'backdrop-filter: blur(4px); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);'
            },
            series: [{
                type: 'treemap',
                left: 0,
                top: 0,
                right: 0,
                bottom: 0,
                roam: false,
                nodeClick: false,
                breadcrumb: { show: false },
                label: {
                    show: true,
                    position: 'insideTopLeft',
                    formatter: function (params) {
                        const d = params.data || {};
                        const rawChange = d.change_pct !== undefined ? d.change_pct : 0;
                        const change = Number.isFinite(Number(rawChange)) ? Number(rawChange) : 0;
                        const sign = change >= 0 ? '+' : '';
                        // ECharts labels don't get much space, so we format compactly
                        let capStr = '--';
                        if (d.value && d.value !== 1) {
                            capStr = (d.value / 100000000).toFixed(0);
                        }

                        let labelStr = `{name|${d.name}} {change|${sign}${change.toFixed(2)}%}\n`;

                        const colorMap = {
                            '#dc2626': 's1', '#ef4444': 's2', '#f59e0b': 's3',
                            '#16a34a': 's4', '#10b981': 's5', '#22c55e': 's6', '#9ca3af': 's7'
                        };
                        const styleName = colorMap[d.analysisColor] || 's7';

                        labelStr += `{rowLabel|情绪:} {${styleName}|${d.analysis}}\n`;
                        labelStr += `{rowLabel|市值:} {rowVal|${capStr}亿}\n`;
                        labelStr += `{rowLabel|换手:} {rowVal|${d.turnover !== null && d.turnover !== undefined ? d.turnover + '%' : '--'}}`;
                        if (d.top_cap_stock) {
                            labelStr += `\n{rowLabel|龙头:} {rowVal|${d.top_cap_stock}}`;
                        }
                        if (d.leading_stock && d.leading_stock !== 'undefined') {
                            labelStr += `\n{rowLabel|领涨:} {rowVal|${d.leading_stock}}`;
                        }
                        if (d.lagging_stock && d.lagging_stock !== 'undefined') {
                            labelStr += `\n{rowLabel|领跌:} {rowVal|${d.lagging_stock}}`;
                        }

                        return labelStr;
                    },
                    rich: {
                        name: { fontSize: 12, fontWeight: 'bold', color: '#fff', padding: [4, 4, 4, 0], textShadowColor: '#000', textShadowBlur: 2 },
                        change: { fontSize: 12, fontWeight: 'bold', color: '#fff', textShadowColor: '#000', textShadowBlur: 2 },
                        rowLabel: { fontSize: 9, color: '#a3a3a3', lineHeight: 14 },
                        rowVal: { fontSize: 9, color: '#f5f5f5' },
                        s1: { fontSize: 9, color: '#fca5a5', fontWeight: 'bold', textShadowColor: '#000', textShadowBlur: 2 },
                        s2: { fontSize: 9, color: '#f87171', fontWeight: 'bold', textShadowColor: '#000', textShadowBlur: 2 },
                        s3: { fontSize: 9, color: '#fcd34d', fontWeight: 'bold', textShadowColor: '#000', textShadowBlur: 2 },
                        s4: { fontSize: 9, color: '#86efac', fontWeight: 'bold', textShadowColor: '#000', textShadowBlur: 2 },
                        s5: { fontSize: 9, color: '#6ee7b7', fontWeight: 'bold', textShadowColor: '#000', textShadowBlur: 2 },
                        s6: { fontSize: 9, color: '#a7f3d0', fontWeight: 'bold', textShadowColor: '#000', textShadowBlur: 2 },
                        s7: { fontSize: 9, color: '#d4d4d8', fontWeight: 'bold', textShadowColor: '#000', textShadowBlur: 2 }
                    }
                },
                itemStyle: {
                    borderColor: '#171717',
                    borderWidth: 1,
                    gapWidth: 1
                },
                data: treeData
            }]
        };

        chart.setOption(option);
        this.charts.set(containerId, chart);
        requestAnimationFrame(() => chart.resize({
            width: dom.clientWidth,
            height: dom.clientHeight
        }));
        return chart;
    }

    // 创建指数估值双轴折线图
    createValuationChart(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) return null;

        // 清理旧实例
        if (this.charts.has(containerId)) {
            this.charts.get(containerId).dispose();
        }

        const chart = echarts.init(container);

        const peSeries = data.pe_series || [];
        const priceSeries = data.price_series || [];

        // 计算近5年时间范围 (默认展示近5年)
        let latestDate = '';
        let startDate = '';
        if (peSeries.length > 0) {
            latestDate = peSeries[peSeries.length - 1][0];
            const latestYear = parseInt(latestDate.substring(0, 4));
            if (!isNaN(latestYear)) {
                startDate = (latestYear - 5) + latestDate.substring(4);
            }
        }

        // 提取分位数线
        const pLines = data.percentile_lines || { p20: 0, p50: 0, p80: 0 };
        const p20 = Number(pLines.p20 || 0);
        const p50 = Number(pLines.p50 || 0);
        const p80 = Number(pLines.p80 || 0);

        // 获取 PE 和价格的最大最小值，用以美化轴间距
        const peValues = peSeries.map(item => item[1]);
        const minPe = Math.floor(Math.min(...peValues, pLines.p20) * 0.9);
        const maxPe = Math.ceil(Math.max(...peValues, pLines.p80) * 1.1);

        const priceValues = priceSeries.map(item => item[1]);
        const minPrice = Math.floor(Math.min(...priceValues) * 0.95);
        const maxPrice = Math.ceil(Math.max(...priceValues) * 1.05);

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross',
                    lineStyle: {
                        color: '#9ca3af',
                        type: 'dashed'
                    }
                },
                formatter: function (params) {
                    if (!params || params.length === 0) return '';
                    let dateStr = params[0].axisValueLabel;
                    let html = `<div style="font-weight: bold; margin-bottom: 4px; color: #1f2937;">${dateStr}</div>`;
                    params.forEach(p => {
                        const marker = p.marker;
                        const seriesName = p.seriesName;
                        const val = p.value[1];
                        if (seriesName.includes('市盈率')) {
                            html += `<div style="color: #4b5563;">${marker} ${seriesName}: <span style="font-weight: bold; font-family: monospace; color: #111827;">${val.toFixed(2)}</span></div>`;
                        } else {
                            html += `<div style="color: #4b5563;">${marker} ${seriesName}: <span style="font-weight: bold; font-family: monospace; color: #111827;">${val.toFixed(0)}</span></div>`;
                        }
                    });
                    return html;
                }
            },
            legend: {
                data: ['市盈率 PE (TTM)', '指数点位'],
                left: 'center',
                top: 15,
                itemGap: 15,
                textStyle: {
                    color: '#4b5563',
                    fontSize: 11
                }
            },
            grid: {
                left: 15,
                right: 15,
                bottom: 50,
                top: 70,
                containLabel: true
            },
            xAxis: {
                type: 'time',
                axisLine: {
                    lineStyle: { color: '#e5e7eb' }
                },
                axisLabel: {
                    color: '#4b5563',
                    formatter: function (value) {
                        const date = new Date(value);
                        return String(date.getFullYear());
                    }
                },
                splitLine: {
                    show: true,
                    lineStyle: { color: '#f3f4f6', type: 'dashed' }
                }
            },
            yAxis: [
                {
                    type: 'value',
                    name: '市盈率PE',
                    min: minPe,
                    max: maxPe,
                    position: 'left',
                    axisLine: {
                        show: true,
                        lineStyle: { color: '#000000', width: 1.5 }
                    },
                    axisLabel: {
                        color: '#000000',
                        fontWeight: 'bold'
                    },
                    splitLine: {
                        show: true,
                        lineStyle: { color: '#f3f4f6' }
                    }
                },
                {
                    type: 'value',
                    name: '点位 (千)',
                    min: minPrice,
                    max: maxPrice,
                    position: 'right',
                    axisLine: {
                        show: true,
                        lineStyle: { color: '#3b82f6', width: 1.5 }
                    },
                    axisLabel: {
                        color: '#3b82f6',
                        fontWeight: 'bold',
                        formatter: function (value) {
                            return (value / 1000).toFixed(0);
                        }
                    },
                    splitLine: {
                        show: false
                    }
                }
            ],
            dataZoom: [
                {
                    type: 'inside',
                    zoomOnMouseWheel: false,  // 禁用鼠标滚轮缩放，解决网页滚动时的误触问题
                    zoomOnMouseButton: false, // 禁用鼠标按键缩放
                    moveOnMouseMove: true,    // 允许鼠标拖拽平移
                    moveOnMouseWheel: false,  // 禁用鼠标滚轮平移
                    startValue: startDate,
                    endValue: latestDate
                },
                {
                    type: 'slider',
                    show: true,
                    startValue: startDate,
                    endValue: latestDate,
                    bottom: '2%',
                    height: 18,
                    borderColor: 'transparent',
                    backgroundColor: '#f3f4f6',
                    fillerColor: 'rgba(59, 130, 246, 0.15)',
                    handleSize: '100%',
                    textStyle: { color: '#9ca3af', fontSize: 10 }
                }
            ],
            series: [
                {
                    name: '市盈率 PE (TTM)',
                    type: 'line',
                    data: peSeries,
                    yAxisIndex: 0,
                    showSymbol: false,
                    smooth: true,
                    itemStyle: {
                        color: '#000000'
                    },
                    lineStyle: {
                        width: 2
                    },
                    markLine: {
                        symbol: 'none',
                        silent: true,
                        label: {
                            formatter: function (params) {
                                return params.name + ': ' + Number(params.value || 0).toFixed(2);
                            },
                            fontSize: 9,
                            fontWeight: 'bold',
                            padding: [2, 4],
                            borderRadius: 3,
                            backgroundColor: 'rgba(255, 255, 255, 0.85)',
                            borderWidth: 1,
                            borderColor: 'rgba(229, 231, 235, 0.5)',
                            offset: [8, 0]
                        },
                        data: [
                            {
                                yAxis: p20,
                                name: '20%',
                                label: {
                                    position: 'insideStartTop',
                                    color: '#15803d'
                                },
                                lineStyle: {
                                    color: '#22c55e',
                                    type: 'dashed',
                                    width: 1.5
                                }
                            },
                            {
                                yAxis: p50,
                                name: '50%',
                                label: {
                                    position: 'insideStartTop',
                                    color: '#4b5563'
                                },
                                lineStyle: {
                                    color: '#6b7280',
                                    type: 'dashed',
                                    width: 1.5
                                }
                            },
                            {
                                yAxis: p80,
                                name: '80%',
                                label: {
                                    position: 'insideStartTop',
                                    color: '#b91c1c'
                                },
                                lineStyle: {
                                    color: '#ef4444',
                                    type: 'dashed',
                                    width: 1.5
                                }
                            }
                        ]
                    }
                },
                {
                    name: '指数点位',
                    type: 'line',
                    data: priceSeries,
                    yAxisIndex: 1,
                    showSymbol: false,
                    smooth: true,
                    itemStyle: {
                        color: '#3b82f6'
                    },
                    lineStyle: {
                        width: 2
                    }
                }
            ]
        };

        chart.setOption(option);
        this.charts.set(containerId, chart);

        window.addEventListener('resize', () => {
            chart.resize();
        });

        return chart;
    }

    // 创建中国央行黄金储备月度净增持柱状图
    createChinaReservesChart(containerId, history) {
        const container = document.getElementById(containerId);
        if (!container) return null;

        if (this.charts.has(containerId)) {
            this.charts.get(containerId).dispose();
        }

        const chart = echarts.init(container);
        const dates = history.map(item => item.date);
        const changes = history.map(item => item.net_change_tonnes);

        const option = {
            ...this.theme,
            tooltip: {
                trigger: 'axis',
                formatter: function (params) {
                    const point = params[0];
                    const val = parseFloat(point.value);
                    const sign = val >= 0 ? '+' : '';
                    return `${point.name}<br/>净买入: ${sign}${val.toFixed(2)} 吨`;
                }
            },
            grid: {
                top: 15,
                bottom: 20,
                left: 45,
                right: 10
            },
            xAxis: {
                type: 'category',
                data: dates,
                axisLabel: {
                    color: this.theme.textStyle.color,
                    formatter: function (value) {
                        if (value.includes('-')) {
                            const parts = value.split('-');
                            return `${parts[0].slice(2)}-${parts[1]}`; // 显示 YY-MM 格式，例如 '24-08'
                        }
                        return value; // 显示年份，例如 '2020年'
                    }
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    color: this.theme.textStyle.color,
                    formatter: '{value}'
                },
                splitLine: {
                    show: true,
                    lineStyle: {
                        color: '#e6e6e6'
                    }
                }
            },
            series: [{
                name: '月度净增持',
                type: 'bar',
                data: changes,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#e5a93b' },
                        { offset: 1, color: '#dfa724' }
                    ]),
                    borderRadius: [2, 2, 0, 0]
                }
            }]
        };

        chart.setOption(option);
        this.charts.set(containerId, chart);

        window.addEventListener('resize', () => {
            chart.resize();
        });

        return chart;
    }

    // 创建SPDR黄金ETF持仓走势图
    createSPDRHoldingsChart(containerId, history) {
        const container = document.getElementById(containerId);
        if (!container) return null;

        if (this.charts.has(containerId)) {
            this.charts.get(containerId).dispose();
        }

        const chart = echarts.init(container);
        const dates = history.map(item => item.date);
        const tonnes = history.map(item => item.tonnes);

        const option = {
            ...this.theme,
            tooltip: {
                trigger: 'axis',
                formatter: function (params) {
                    const point = params[0];
                    const idx = point.dataIndex;
                    const item = history[idx];
                    if (!item) return '';
                    const sign = item.change >= 0 ? '+' : '';
                    return `${item.date}<br/>总持仓: ${item.tonnes.toLocaleString()} 吨<br/>单日变动: ${sign}${item.change.toFixed(2)} 吨`;
                }
            },
            grid: {
                top: 15,
                bottom: 20,
                left: 55,
                right: 15
            },
            xAxis: {
                type: 'category',
                data: dates,
                axisLabel: {
                    color: this.theme.textStyle.color,
                    formatter: function (value) {
                        if (value.includes('-')) {
                            const parts = value.split('-');
                            if (parts.length >= 3) {
                                return `${parts[1]}-${parts[2]}`; // 日度显示 MM-DD
                            }
                            return `${parts[0].slice(2)}-${parts[1]}`; // 月度显示 YY-MM，例如 '26-08'
                        }
                        return value; // '2020年'
                    }
                }
            },
            yAxis: {
                type: 'value',
                scale: true,
                axisLabel: {
                    color: this.theme.textStyle.color,
                    formatter: '{value}'
                },
                splitLine: {
                    show: true,
                    lineStyle: {
                        color: '#e6e6e6'
                    }
                }
            },
            series: [{
                name: '持仓总量',
                type: 'line',
                data: tonnes,
                showSymbol: false,
                lineStyle: {
                    color: '#dfa724',
                    width: 2
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(223, 167, 36, 0.3)' },
                        { offset: 1, color: 'rgba(223, 167, 36, 0.0)' }
                    ])
                }
            }]
        };

        chart.setOption(option);
        this.charts.set(containerId, chart);

        window.addEventListener('resize', () => {
            chart.resize();
        });

        return chart;
    }
}

// 创建全局图表实例
window.charts = new Charts();
