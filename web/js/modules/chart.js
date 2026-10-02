// 指数估值与走势图表模块控制器
// 依赖: utils.js, api.js, charts.js

class ChartController {
    constructor() {
        this.currentValuationIndex = 'NDX';
        this.valuationTabsBound = false;
    }

    async loadData() {
        console.log('📈 加载指数估值温度计数据...');

        // 检查 URL 是否指定了特定指数 (如 ?tab=chart&index=SP500)
        const urlCode = utils.getUrlParam('index') || utils.getUrlParam('code') || utils.getUrlParam('symbol');
        if (urlCode) {
            this.currentValuationIndex = urlCode.toUpperCase();
        }

        // 绑定估值 tab 事件与说明弹窗
        if (!this.valuationTabsBound) {
            this.bindValuationTabs();
            this.valuationTabsBound = true;
        } else {
            // 同步当前激活的按钮样式
            this.syncActiveTabButton();
        }

        await this.loadValuation(this.currentValuationIndex);
    }

    syncActiveTabButton() {
        const tabs = document.querySelectorAll('#chart .val-tab, .valuation-tabs .val-tab');
        tabs.forEach(tab => {
            const code = (tab.dataset.code || '').toUpperCase();
            tab.classList.toggle('active', code === this.currentValuationIndex);
        });
    }

    bindValuationTabs() {
        const tabs = document.querySelectorAll('#chart .val-tab, .valuation-tabs .val-tab');
        
        // 初始高亮检查
        tabs.forEach(tab => {
            const code = (tab.dataset.code || '').toUpperCase();
            tab.classList.toggle('active', code === this.currentValuationIndex);
            
            tab.onclick = () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentValuationIndex = (tab.dataset.code || 'NDX').toUpperCase();

                // 更新 URL 参数 (NDX 为默认值，非 NDX 时保留 index 参数)
                const url = new URL(window.location.href);
                if (this.currentValuationIndex !== 'NDX') {
                    url.searchParams.set('index', this.currentValuationIndex);
                } else {
                    url.searchParams.delete('index');
                }
                window.history.replaceState({}, '', url.toString());

                this.loadValuation(this.currentValuationIndex);
            };
        });

        // 绑定指数估值问号说明弹窗
        const infoBtn = document.getElementById('info-index-valuation');
        if (infoBtn) {
            infoBtn.style.display = 'flex';
            infoBtn.onclick = () => utils.showInfoModal('指数估值温度计说明',
`通过对比市盈率 PE (TTM) 与自身历史百分位，评估指数估值性价比。

1. 滚动统计窗口
基于近 10 年滚动历史数据计算，避免跨行业横向比较的偏差。

2. 曲线与分位线
· 黑色曲线：市盈率 PE (TTM)（对应左轴）
· 蓝色曲线：指数收盘点位（对应右轴）
· 80% 警戒线：代表估值偏贵，警惕回调风险。
· 50% 中位线：估值处于历史中位数合理中枢。
· 20% 安全线：代表性价比高，进入低估区。

3. 评级标准
· 低估 (<20%) / 适中 (20%~80%) / 高估 (>=80%)

免责声明：本数据仅供参考，不构成任何投资买卖建议。`);
        }
    }

    async loadValuation(indexCode) {
        const container = document.getElementById('valuation-chart');
        const summaryContainer = document.getElementById('valuation-summary');
        if (!container) return;

        // 1. 先安全销毁 ECharts 实例，再清空 innerHTML (避免 removeChild 报错)
        if (typeof echarts !== 'undefined') {
            const oldInstance = echarts.getInstanceByDom(container);
            if (oldInstance) {
                try {
                    oldInstance.dispose();
                } catch (e) {
                    console.warn('Safe dispose failed:', e);
                }
            }
        }
        if (window.charts && window.charts.charts && window.charts.charts.has('valuation-chart')) {
            try {
                window.charts.charts.get('valuation-chart').dispose();
            } catch (e) {
                console.warn('Safe registry dispose failed:', e);
            }
            window.charts.charts.delete('valuation-chart');
        }

        // 2. 呈现加载状态
        container.innerHTML = '<div class="loading">Loading...</div>';
        if (summaryContainer) {
            summaryContainer.innerHTML = '<span style="color: var(--text-secondary);">正在获取估值数据...</span>';
        }

        try {
            const res = await api.getIndexValuation(indexCode);
            if (res._warming_up) {
                container.innerHTML = `<div class="loading">${res.message || '数据预热中，请稍后刷新'}</div>`;
                if (summaryContainer) {
                    summaryContainer.innerHTML = `<span style="color: var(--text-secondary);">${res.message || '数据预热中...'}</span>`;
                }
                return;
            }
            if (res._error) {
                container.innerHTML = `<div class="loading error">${res.message || '数据获取失败'}</div>`;
                if (summaryContainer) summaryContainer.innerHTML = '';
                return;
            }
            if (!res.pe_series || res.pe_series.length === 0) {
                container.innerHTML = '<div class="loading error">数据不可用</div>';
                if (summaryContainer) summaryContainer.innerHTML = '';
                return;
            }

            // 上报时间
            if (res.data_date && window.app && typeof window.app.reportDataTime === 'function') {
                window.app.reportDataTime(res.data_date);
            }

            // 更新估值摘要
            if (summaryContainer) {
                const name = res.name || indexCode;
                const date = res.data_date || '';
                const peVal = res.current_pe != null ? Number(res.current_pe).toFixed(2) : '--';
                const pct = res.percentile != null ? (Number(res.percentile) * 100).toFixed(0) : '--';
                const level = res.eval_level || 'medium';

                let levelName = '估值适中';
                let badgeClass = 'medium';
                if (level === 'low') {
                    levelName = '低估';
                    badgeClass = 'low';
                } else if (level === 'high') {
                    levelName = '高估';
                    badgeClass = 'high';
                }

                const headerTitle = document.getElementById('val-header-title');
                const headerBadge = document.getElementById('val-header-badge');
                if (headerTitle) headerTitle.textContent = `${name} 估值概览`;
                if (headerBadge) {
                    headerBadge.textContent = levelName;
                    headerBadge.className = `status-badge ${badgeClass}`;
                }

                const indexDescriptions = {
                    'NDX': '纳斯达克100指数由纳斯达克市场中100家最具创新力的非金融大企业组成，是全球科技股和成长股的黄金标杆。',
                    'SP500': '标普500指数代表美国最具影响力的500家行业龙头企业，被视为衡量美国股市大盘整体健康状况的最佳基准。',
                    'HSI': '恒生指数由香港交易所最大、流动性最好的蓝筹股组成，综合反映了香港及海外中概核心资产的整体表现。',
                    'SH000300': '沪深300指数精选沪深市场中规模大、流动性好的最具代表性的300只龙头股票，是中国A股大盘走势的晴雨表。',
                    'SH000015': '中证红利指数挑选沪深市场中分红高、股息率稳定、规模居前的100只股票，反映高股息资产在市场震荡下的稳健表现。',
                    'SH000688': '科创50指数由科创板中市值大、流动性好的50只硬科技证券组成，涵盖半导体、生物医药、高端制造等关键前沿科技。',
                    'SZ399006': '创业板指代表深交所创业板中市值与流动性排名前100的企业，聚焦新能源、生物医药、TMT等战略性高成长新兴产业。',
                    'SH000905': '中证500指数扣除大盘蓝筹后，选取沪深市场中日均总市值排名前500的中小市值企业，反映成长型中盘骨干企业的整体面貌。',
                    'SH000016': '上证50指数挑选沪市最具市场影响力的50只超大型核心蓝筹，集中分布于金融、消费等传统实体行业巨头。',
                    'SH000932': '中证消费指数精选主要消费行业中实力雄厚的代表性股票（如高端白酒、食品饮料），是长期收益优异的刚需消费赛道。'
                };

                const desc = indexDescriptions[indexCode.toUpperCase()] || '该指数用于评估特定市场或行业的估值性价比。';

                summaryContainer.innerHTML = `
                    <div class="val-summary-stats">
                        <div class="val-stats-group">
                            <div class="val-stat-item">
                                <span class="val-stat-label">当前 PE (TTM)</span>
                                <span class="val-stat-value">${peVal}</span>
                            </div>
                            <div class="val-stat-item">
                                <span class="val-stat-label">历史估值百分位</span>
                                <span class="val-stat-value">${pct}%</span>
                            </div>
                            <div class="val-stat-item val-stat-date">
                                <span class="val-stat-label">数据截止日期</span>
                                <span class="val-stat-value">${date}</span>
                            </div>
                        </div>
                        <div class="val-desc-group">
                            <span class="val-desc-text">${desc}</span>
                        </div>
                    </div>
                `;
            }

            // 渲染折线图
            charts.createValuationChart('valuation-chart', res);

        } catch (error) {
            console.error('加载指数估值失败:', error);
            container.innerHTML = `<div class="loading error">指数估值数据加载失败: ${error.message || error}</div>`;
            if (summaryContainer) summaryContainer.innerHTML = '';
        }
    }
}
