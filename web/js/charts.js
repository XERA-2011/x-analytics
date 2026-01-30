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

        // 根据分数确定颜色
        let color;
        if (score >= 80) color = '#ef4444'; // 极度贪婪 - 红色
        else if (score >= 65) color = '#f59e0b'; // 贪婪 - 橙色
        else if (score >= 55) color = '#eab308'; // 轻微贪婪 - 黄色
        else if (score >= 45) color = '#6b7280'; // 中性 - 灰色
        else if (score >= 35) color = '#3b82f6'; // 轻微恐慌 - 蓝色
        else if (score >= 20) color = '#8b5cf6'; // 恐慌 - 紫色
        else color = '#10b981'; // 极度恐慌 - 绿色

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

        // 格式化数据结构
        const treeData = data.map(item => ({
            name: item.name,
            value: item.value, // 市值 (数值)

            // 自定义属性
            change_pct: item.change_pct,
            leading_stock: item.leading_stock,
            stock_count: item.stock_count,
            turnover: item.turnover,

            itemStyle: {
                color: item.change_pct >= 0
                    ? `rgba(239, 68, 68, ${Math.min(0.3 + item.change_pct / 10, 1)})` // Red
                    : `rgba(34, 197, 94, ${Math.min(0.3 + Math.abs(item.change_pct) / 10, 1)})` // Green
            }
        }));

        const option = {
            backgroundColor: "transparent",
            tooltip: {
                trigger: 'item',
                formatter: function (info) {
                    const d = info.data;
                    const change = d.change_pct ?? 0;
                    const color = change >= 0 ? "#ef4444" : "#22c55e";
                    const capStr = d.value ? (d.value / 100000000).toFixed(0) : '--';

                    return `
                        <div style="min-width: 120px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px solid #404040;">
                                <span style="font-weight: 700; font-size: 14px; color: #fff;">${d.name}</span>
                                <span style="font-weight: 700; font-family: monospace; font-size: 14px; color:${color}">${change >= 0 ? '+' : ''}${change.toFixed(2)}%</span>
                            </div>
                            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                                <tr style="line-height: 1.6;">
                                    <td style="color: #9ca3af; padding-right: 12px;">市值</td>
                                    <td style="text-align: right; font-family: monospace; color: #e5e7eb;">${capStr}亿</td>
                                </tr>
                                <tr style="line-height: 1.6;">
                                    <td style="color: #9ca3af; padding-right: 12px;">家数</td>
                                    <td style="text-align: right; font-family: monospace; color: #e5e7eb;">${d.stock_count}</td>
                                </tr>
                                <tr style="line-height: 1.6;">
                                    <td style="color: #9ca3af; padding-right: 12px;">换手</td>
                                    <td style="text-align: right; font-family: monospace; color: #e5e7eb;">${d.turnover}%</td>
                                </tr>
                                <tr style="line-height: 1.6;">
                                    <td style="color: #9ca3af; padding-right: 12px;">领涨</td>
                                    <td style="text-align: right; color: #e5e7eb; max-width: 65px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${d.leading_stock}</td>
                                </tr>
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
                    formatter: function (params) {
                        const d = params.data;
                        return `{name|${d.name}}\n{val|${d.change_pct.toFixed(2)}%}`;
                    },
                    rich: {
                        name: {
                            fontSize: 13,
                            fontWeight: 'bold',
                            color: '#fff',
                            textShadowColor: 'rgba(0,0,0,0.8)',
                            textShadowBlur: 3,
                            padding: [0, 0, 4, 0]
                        },
                        val: {
                            fontSize: 11,
                            color: '#f5f5f5',
                            textShadowColor: 'rgba(0,0,0,0.8)',
                            textShadowBlur: 3
                        }
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