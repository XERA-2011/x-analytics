// 图表组件模块

class Charts {
    constructor() {
        this.charts = new Map();
        this.theme = this.getTheme();
    }

    // 获取主题配置
    getTheme() {
        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        return {
            backgroundColor: 'transparent',
            textStyle: {
                color: isDark ? '#f8fafc' : '#0f172a',
                fontFamily: 'Fira Sans, sans-serif'
            },
            grid: {
                borderColor: isDark ? '#334155' : '#e2e8f0'
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
        
        const score = data.score || 50;
        const level = data.level || '中性';
        
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
                formatter: function(params) {
                    const point = params[0];
                    return `${point.name}: ${point.value}%`;
                }
            },
            xAxis: {
                type: 'category',
                data: periods,
                axisLabel: {
                    color: this.theme.textStyle.color
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    formatter: '{value}%',
                    color: this.theme.textStyle.color
                }
            },
            series: [{
                data: yields,
                type: 'line',
                smooth: true,
                lineStyle: {
                    color: '#3b82f6',
                    width: 3
                },
                itemStyle: {
                    color: '#3b82f6'
                },
                areaStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                            { offset: 1, color: 'rgba(59, 130, 246, 0.1)' }
                        ]
                    }
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
                formatter: function(params) {
                    const point = params[0];
                    return `${point.name}<br/>金银比: ${point.value}`;
                }
            },
            xAxis: {
                type: 'category',
                data: dates,
                axisLabel: {
                    color: this.theme.textStyle.color,
                    formatter: function(value) {
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
                    color: '#f59e0b',
                    width: 2
                },
                itemStyle: {
                    color: '#f59e0b'
                },
                areaStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: 'rgba(245, 158, 11, 0.3)' },
                            { offset: 1, color: 'rgba(245, 158, 11, 0.1)' }
                        ]
                    }
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
            chart.resize();
        });
    }
}

// 创建全局图表实例
window.charts = new Charts();