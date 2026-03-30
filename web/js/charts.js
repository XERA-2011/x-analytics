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

    // 创建恐慌贪婪指数仪表盘
    createFearGreedGauge(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) return null;

        // 清理现有图表
        if (this.charts.has(containerId)) {
            this.charts.get(containerId).dispose();
        }

        const chart = echarts.init(container);

        const score = data.score ?? data.current_value;
        const level = data.level || data.current_level || '未知';

        // 如果没有分数数据，不渲染图表
        if (score == null) {
            container.innerHTML = '<div class="loading error">数据不可用</div>';
            return null;
        }

        // 根据分数确定颜色（优先使用后端 levels 配置）
        const levels = Array.isArray(data.levels) ? data.levels.slice() : null;
        let color;
        const palette7 = ['#ef4444', '#f59e0b', '#eab308', '#6b7280', '#3b82f6', '#8b5cf6', '#10b981'];
        const palette5 = ['#ef4444', '#f59e0b', '#6b7280', '#3b82f6', '#10b981'];

        if (levels && levels.length > 0) {
            levels.sort((a, b) => b.min - a.min);
            const palette = levels.length === 5 ? palette5 : palette7;
            let idx = levels.findIndex(l => score >= l.min);
            if (idx === -1) idx = levels.length - 1;
            color = palette[Math.min(idx, palette.length - 1)];
        } else {
            if (score >= 80) color = '#ef4444'; // 极度贪婪 - 红色
            else if (score >= 65) color = '#f59e0b'; // 贪婪 - 橙色
            else if (score >= 55) color = '#eab308'; // 轻微贪婪 - 黄色
            else if (score >= 45) color = '#6b7280'; // 中性 - 灰色
            else if (score >= 35) color = '#3b82f6'; // 轻微恐慌 - 蓝色
            else if (score >= 20) color = '#8b5cf6'; // 恐慌 - 紫色
            else color = '#10b981'; // 极度恐慌 - 绿色
        }

        const option = {
            series: [{
                type: 'gauge',
                center: ['50%', '55%'],
                radius: '90%',
                startAngle: 200,
                endAngle: -20,
                min: 0,
                max: 100,
                splitNumber: 5,
                itemStyle: {
                    color: color
                },
                progress: {
                    show: true,
                    width: 12
                },
                pointer: {
                    show: false
                },
                axisLine: {
                    lineStyle: {
                        width: 12,
                        color: [[1, '#e5e7eb']]
                    }
                },
                axisTick: {
                    distance: -20,
                    splitNumber: 5,
                    lineStyle: {
                        width: 1,
                        color: '#999'
                    }
                },
                splitLine: {
                    distance: -20,
                    length: 8,
                    lineStyle: {
                        width: 2,
                        color: '#999'
                    }
                },
                axisLabel: {
                    distance: -15,
                    color: '#999',
                    fontSize: 8
                },
                anchor: {
                    show: false
                },
                title: {
                    show: false
                },
                detail: {
                    valueAnimation: true,
                    width: '60%',
                    lineHeight: 20,
                    borderRadius: 4,
                    offsetCenter: [0, '-10%'],
                    fontSize: 16,
                    fontWeight: 'bold',
                    formatter: '{value}',
                    color: color
                },
                data: [{
                    value: score
                }]
            }]
        };

        chart.setOption(option);
        this.charts.set(containerId, chart);

        // 添加响应式处理
        window.addEventListener('resize', () => {
            chart.resize();
        });

        return chart;
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

        const chart = echarts.init(dom, "dark");

        const getSentiment = (c, t) => {
            let analysis = "中性";
            let analysisColor = "#9ca3af";
            const absC = Math.abs(c);

            if (absC < 0.8) {
                analysis = "横盘震荡";
                analysisColor = "#9ca3af";
            } else if (c > 0) {
                if (c > 8) { analysis = t > 2 ? "极度超买" : "逼空拉升"; analysisColor = "#dc2626"; }
                else if (t > 5 && c > 4) { analysis = "严重超买"; analysisColor = "#dc2626"; }
                else if (t > 3 || c > 4) { analysis = "放量上攻"; analysisColor = "#ef4444"; }
                else if (t < 1.2 && c < 2) { analysis = "缩量上涨"; analysisColor = "#f59e0b"; }
                else { analysis = "温和上涨"; analysisColor = "#ef4444"; }
            } else {
                if (c < -8) { analysis = t > 2 ? "恐慌抛售" : "闷杀出局"; analysisColor = "#16a34a"; }
                else if (t > 5 && c < -4) { analysis = "恐慌抛售"; analysisColor = "#16a34a"; }
                else if (t > 3 || c < -4) { analysis = "放量杀跌"; analysisColor = "#16a34a"; }
                else if (t < 1.2 && c > -2) { analysis = "无量下跌"; analysisColor = "#10b981"; }
                else { analysis = "弱势调整"; analysisColor = "#22c55e"; }
            }
            return { analysis, analysisColor };
        };

        const treeData = data.map(item => {
            const change = Number.isFinite(Number(item.change_pct)) ? Number(item.change_pct) : 0;
            const turnover = Number.isFinite(Number(item.turnover)) ? Number(item.turnover) : 0;
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
                value: item.value || 1, // Fallback to 1 to ensure it renders
                change_pct: change,
                top_cap_stock: topCapStockStr,
                leading_stock: leadingStr,
                lagging_stock: laggingStr,
                turnover: turnover,
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
                    const d = info.data || params.data; // Unified variable pull for safety
                    const rawChange = d ? (d.change_pct !== undefined ? d.change_pct : 0) : 0;
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
                                    <td style="text-align: right; font-family: monospace; color: #e5e7eb;">${d.turnover}%</td>
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
                width: '100%',
                height: '100%',
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
                        labelStr += `{rowLabel|换手:} {rowVal|${d.turnover}%}`;

                        // Custom conditionals for trailing properties
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
        window.addEventListener("resize", () => chart.resize());
        return chart;
    }
}

// 创建全局图表实例
window.charts = new Charts();
