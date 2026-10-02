// 指数估值与全球主要指数对比模块控制器
// 依赖: utils.js, api.js, charts.js

class ChartController {
    constructor() {
        this.currentValuationIndex = 'NDX';
        this.valuationTabsBound = false;

        // 全球指数对比模块状态
        this.indicesRawData = null;
        this.currentPeriod = 'ytd';
        this.selectedIndices = new Set(['NDX', 'SP500', 'SH000300', 'HSI', 'N225', 'KOSPI']);
        this.comparisonEventsBound = false;
        this.matrixSortCol = 'YTD';
        this.matrixSortDesc = true;
    }

    async loadData() {
        console.log('📈 加载图表中心数据...');

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
            this.syncActiveTabButton();
        }

        // 绑定指数对比事件
        if (!this.comparisonEventsBound) {
            this.bindComparisonEvents();
            this.comparisonEventsBound = true;
        }

        // 并行加载全球指数对比与估值温度计
        await Promise.allSettled([
            this.loadIndicesComparison(),
            this.loadValuation(this.currentValuationIndex)
        ]);
    }

    // =========================================================================
    // 全球主要多国指数对比逻辑
    // =========================================================================

    async loadIndicesComparison() {
        const chartContainer = document.getElementById('indices-comparison-chart');
        const matrixContainer = document.getElementById('indices-matrix-container');
        if (!chartContainer) return;

        // 呈现加载态
        chartContainer.innerHTML = '<div class="loading">Loading...</div>';
        if (matrixContainer) {
            matrixContainer.innerHTML = '<div class="loading">Loading...</div>';
        }

        try {
            const res = await api.getIndicesComparison();
            if (res && res._warming_up) {
                chartContainer.innerHTML = `<div class="loading">${res.message || '全球指数数据预热中，请稍后刷新'}</div>`;
                if (matrixContainer) matrixContainer.innerHTML = `<div class="loading">${res.message || '数据预热中...'}</div>`;
                return;
            }
            if (res && res._error) {
                chartContainer.innerHTML = `<div class="loading error">${res.message || '全球指数数据获取失败'}</div>`;
                if (matrixContainer) matrixContainer.innerHTML = '';
                return;
            }

            const indices = res && res.data ? res.data.indices : (res && res.indices ? res.indices : []);
            if (!indices || indices.length === 0) {
                chartContainer.innerHTML = '<div class="loading error">全球指数数据不可用</div>';
                if (matrixContainer) matrixContainer.innerHTML = '';
                return;
            }

            this.indicesRawData = indices;

            // 更新顶部最新数据日期角标
            let latestDateStr = '';
            indices.forEach(idx => {
                if (idx.latest_date && idx.latest_date > latestDateStr) {
                    latestDateStr = idx.latest_date;
                }
            });
            const dateBadge = document.getElementById('indices-latest-date');
            if (dateBadge && latestDateStr) {
                dateBadge.textContent = `最新收盘: ${latestDateStr}`;
                dateBadge.style.display = 'inline-block';
            }

            // 渲染筛选标签
            this.renderIndexChips();

            // 绘制归一化对比折线图
            this.updateComparisonChart();

            // 绘制多周期收益率看板
            this.renderPerformanceMatrix();

        } catch (error) {
            console.error('加载全球指数走势对比失败:', error);
            if (chartContainer) {
                chartContainer.innerHTML = `<div class="loading error">全球指数对比加载失败: ${error.message || error}</div>`;
            }
            if (matrixContainer) matrixContainer.innerHTML = '';
        }
    }

    bindComparisonEvents() {
        // 1. 周期切换 Pills
        const pills = document.querySelectorAll('#indices-period-pills .period-pill');
        pills.forEach(pill => {
            pill.onclick = () => {
                pills.forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                this.currentPeriod = pill.dataset.period || 'ytd';
                this.matrixSortCol = this.currentPeriod.toUpperCase();
                this.updateComparisonChart();
                this.renderPerformanceMatrix();
            };
        });

        // 2. 工具栏快捷按钮 (默认、全选)
        const btnDefault = document.getElementById('btn-select-default-indices');
        if (btnDefault) {
            btnDefault.onclick = () => {
                const defaults = this.indicesRawData
                    ? this.indicesRawData.filter(i => i.default_selected).map(i => i.code)
                    : ['NDX', 'SP500', 'SH000300', 'HSI', 'N225', 'KOSPI'];
                this.selectedIndices = new Set(defaults.length > 0 ? defaults : ['NDX', 'SP500', 'SH000300', 'HSI', 'N225', 'KOSPI']);
                this.renderIndexChips();
                this.updateComparisonChart();
                this.renderPerformanceMatrix();
            };
        }

        const btnAll = document.getElementById('btn-select-all-indices');
        if (btnAll) {
            btnAll.onclick = () => {
                if (this.indicesRawData) {
                    this.selectedIndices = new Set(this.indicesRawData.map(i => i.code));
                    this.renderIndexChips();
                    this.updateComparisonChart();
                    this.renderPerformanceMatrix();
                }
            };
        }

        // 3. 说明问号弹窗
        const infoBtn = document.getElementById('info-indices-comparison');
        if (infoBtn) {
            infoBtn.style.display = 'flex';
            infoBtn.onclick = () => utils.showInfoModal('全球主要指数对比说明',
`本模块用于直观对比全球各核心股票市场在不同时间跨度下的相对涨跌强弱与联动节奏。

1. 基准归一化累计走势（Normalized % Return）
· 以所选周期起点日（Base Date）为基准设为 0.00%，后续每日取收盘价计算相对于起点的累计涨跌幅百分比：(收盘价 - 基准价) / 基准价 × 100%。
· 消除由于纳指(30,000+)、日经(68,000+)、沪深300(4,000+)等点位基数悬殊带来的不可比性。

2. 多国交易日历自适应对齐（Calendar Alignment）
· 自动汇总中、美、港、欧、日、韩、印各交易所的全部有效交易日。
· 针对各国不同法定节假日休市，采用前向填充（Forward Fill）算法沿用最新收盘价，确保跨国走势曲线平滑连贯无断点。

3. 智能动态排行榜 Tooltip
· 鼠标悬浮查看任意交易日时，列表自动按照当日累计收益率从高到低倒序排序，前三名带有金银铜奖牌标示。

4. 颜色与涨跌规则
· 严格遵循国内金融规范：红涨绿跌。

5. 顺畅页面滚动与快捷缩放
· 滚轮穿透：在图表区域内滑动滚轮不会阻断网页正常上下滚动；
· 精细缩放：如需局部放大缩小图表，按住 Ctrl（Mac 用户按 Command ⌘）滚动滚轮即可，亦可直接拖拽底部时间轴滑块。

免责声明：本数据仅供参考，不构成任何投资买卖建议。`);
        }
    }

    renderIndexChips() {
        const container = document.getElementById('index-chips-container');
        if (!container || !this.indicesRawData) return;

        container.innerHTML = this.indicesRawData.map(item => {
            const isSelected = this.selectedIndices.has(item.code);
            const activeStyle = isSelected
                ? `background-color: ${item.color}; border-color: ${item.color}; color: #ffffff; font-weight: 600; box-shadow: 0 2px 6px ${item.color}45;`
                : `background-color: var(--bg-subtle, #f3f4f6); border-color: var(--border-light, #e5e7eb); color: var(--text-secondary, #4b5563);`;
            const dotStyle = isSelected
                ? `background-color: #ffffff;`
                : `background-color: ${item.color};`;
            return `
                <button class="index-chip ${isSelected ? 'active' : ''}" data-code="${item.code}" style="${activeStyle}">
                    <span class="chip-color-dot" style="${dotStyle}"></span>
                    <span class="chip-name">${item.name}</span>
                </button>
            `;
        }).join('');

        // 绑定点击事件
        container.querySelectorAll('.index-chip').forEach(btn => {
            btn.onclick = () => {
                const code = btn.dataset.code;
                if (!code) return;

                if (this.selectedIndices.has(code)) {
                    if (this.selectedIndices.size <= 1) return; // 至少保留 1 个
                    this.selectedIndices.delete(code);
                } else {
                    this.selectedIndices.add(code);
                }

                this.renderIndexChips();
                this.updateComparisonChart();
                this.renderPerformanceMatrix();
            };
        });
    }

    getStartDateForPeriod(period, latestDateStr) {
        const refDate = latestDateStr ? new Date(latestDateStr) : new Date();
        const d = new Date(refDate.getTime());
        switch ((period || 'ytd').toLowerCase()) {
            case '1m':
                d.setDate(d.getDate() - 30);
                break;
            case '3m':
                d.setDate(d.getDate() - 90);
                break;
            case '6m':
                d.setDate(d.getDate() - 180);
                break;
            case 'ytd':
                return `${refDate.getFullYear() - 1}-12-31`;
            case '1y':
                d.setFullYear(d.getFullYear() - 1);
                break;
            case '3y':
                d.setFullYear(d.getFullYear() - 3);
                break;
            default:
                return `${refDate.getFullYear() - 1}-12-31`;
        }
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    updateComparisonChart() {
        if (!this.indicesRawData || this.indicesRawData.length === 0) return;

        // 找出所有选中指数的数据
        const selectedItems = this.indicesRawData.filter(i => this.selectedIndices.has(i.code));
        if (selectedItems.length === 0) return;

        // 找到最新日期作为周期参考点
        let globalLatestDate = '';
        selectedItems.forEach(item => {
            if (item.latest_date && item.latest_date > globalLatestDate) {
                globalLatestDate = item.latest_date;
            }
        });

        const startDate = this.getStartDateForPeriod(this.currentPeriod, globalLatestDate);

        // 收集所有选中指数在 startDate 之后的交易日并集
        const dateSet = new Set();
        selectedItems.forEach(item => {
            (item.history || []).forEach(h => {
                const d = h[0];
                if (d >= startDate) {
                    dateSet.add(d);
                }
            });
        });

        const unifiedDates = Array.from(dateSet).sort();
        if (unifiedDates.length === 0) return;

        // 对每个选中指数计算归一化累计涨跌幅，并使用 ffill 填充休市日
        const series = selectedItems.map(item => {
            const hist = item.history || [];
            const dateToClose = new Map();
            hist.forEach(h => {
                if (h[1] != null && h[1] > 0) {
                    dateToClose.set(h[0], h[1]);
                }
            });

            // 确定起点基准价格 (在 startDate 当天或之前的最近一个有效正收盘价)
            let basePrice = null;
            for (let i = hist.length - 1; i >= 0; i--) {
                if (hist[i][0] <= startDate && hist[i][1] != null && hist[i][1] > 0) {
                    basePrice = hist[i][1];
                    break;
                }
            }
            if (basePrice == null && hist.length > 0) {
                const validFirst = hist.find(h => h[1] != null && h[1] > 0);
                basePrice = validFirst ? validFirst[1] : null;
            }

            let lastClose = basePrice;
            const returns = [];

            unifiedDates.forEach(date => {
                if (dateToClose.has(date)) {
                    const c = dateToClose.get(date);
                    if (c != null && c > 0) {
                        lastClose = c;
                    }
                }
                // 计算相对于基准价格的累计收益率
                if (basePrice && basePrice > 0 && lastClose != null && lastClose > 0) {
                    const ret = ((lastClose - basePrice) / basePrice) * 100;
                    returns.push(Number(ret.toFixed(2)));
                } else {
                    returns.push(0);
                }
            });

            return {
                code: item.code,
                name: item.name,
                fullName: item.full_name,
                flag: item.flag,
                color: item.color,
                data: returns
            };
        });

        // 调用 ECharts 渲染
        charts.createMultiIndexComparisonChart('indices-comparison-chart', {
            dates: unifiedDates,
            series: series
        });
    }

    renderPerformanceMatrix() {
        const container = document.getElementById('indices-matrix-container');
        if (!container || !this.indicesRawData) return;

        // 复制数据用于排序
        let list = [...this.indicesRawData];

        const sortCol = this.matrixSortCol || 'YTD';
        const isDesc = this.matrixSortDesc !== false;

        list.sort((a, b) => {
            let valA, valB;
            if (sortCol === 'latest_close') {
                valA = a.latest_close || 0;
                valB = b.latest_close || 0;
            } else if (sortCol === 'name') {
                return isDesc ? b.name.localeCompare(a.name) : a.name.localeCompare(b.name);
            } else {
                valA = a.returns && a.returns[sortCol] != null ? a.returns[sortCol] : -99999;
                valB = b.returns && b.returns[sortCol] != null ? b.returns[sortCol] : -99999;
            }
            return isDesc ? valB - valA : valA - valB;
        });

        const periods = ['1D', '1W', '1M', '3M', '6M', 'YTD', '1Y', '3Y'];
        const periodLabels = {
            '1D': '日涨跌',
            '1W': '近1周',
            '1M': '近1月',
            '3M': '近3月',
            '6M': '近6月',
            'YTD': '今年以来',
            '1Y': '近1年',
            '3Y': '近3年'
        };

        const activePeriodKey = this.currentPeriod.toUpperCase();

        let tableHtml = `
            <div class="matrix-table-wrap">
                <table class="matrix-table">
                    <thead>
                        <tr>
                            <th class="col-index sortable" data-sort="name">指数名称</th>
                            <th class="col-close sortable text-right" data-sort="latest_close">最新收盘</th>
                            ${periods.map(p => {
                                const isSort = sortCol === p;
                                const sortIcon = isSort ? (isDesc ? ' ▼' : ' ▲') : '';
                                const isCurrent = activePeriodKey === p ? 'current-period-header' : '';
                                return `<th class="col-ret sortable text-right ${isCurrent}" data-sort="${p}">${periodLabels[p]}${sortIcon}</th>`;
                            }).join('')}
                        </tr>
                    </thead>
                    <tbody>
        `;

        list.forEach(item => {
            const isSelected = this.selectedIndices.has(item.code);
            const closeFormatted = item.latest_close != null ? Number(item.latest_close).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--';

            tableHtml += `
                <tr class="matrix-row ${isSelected ? 'row-selected' : ''}" data-code="${item.code}" title="点击在走势图中开启/关闭该指数">
                    <td class="col-index">
                        <div class="matrix-index-cell">
                            <span class="chip-color-dot" style="background-color: ${item.color};"></span>
                            <span class="matrix-name">${item.name}</span>
                            <span class="matrix-code">${item.code}</span>
                        </div>
                    </td>
                    <td class="col-close text-right font-mono">${closeFormatted}</td>
                    ${periods.map(p => {
                        const val = item.returns ? item.returns[p] : null;
                        let valStr = '--';
                        let cls = 'val-flat';
                        if (val != null) {
                            valStr = (val > 0 ? '+' : '') + Number(val).toFixed(2) + '%';
                            cls = val > 0 ? 'val-up' : (val < 0 ? 'val-down' : 'val-flat');
                        }
                        const isCurrentCol = activePeriodKey === p ? 'current-period-cell' : '';
                        return `<td class="col-ret text-right font-mono ${cls} ${isCurrentCol}">${valStr}</td>`;
                    }).join('')}
                </tr>
            `;
        });

        tableHtml += `
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = tableHtml;

        // 绑定表头排序
        container.querySelectorAll('th.sortable').forEach(th => {
            th.onclick = (e) => {
                e.stopPropagation();
                const col = th.dataset.sort;
                if (!col) return;
                if (this.matrixSortCol === col) {
                    this.matrixSortDesc = !this.matrixSortDesc;
                } else {
                    this.matrixSortCol = col;
                    this.matrixSortDesc = true;
                }
                this.renderPerformanceMatrix();
            };
        });

        // 绑定行点击联动开关
        container.querySelectorAll('tr.matrix-row').forEach(row => {
            row.onclick = () => {
                const code = row.dataset.code;
                if (!code) return;

                if (this.selectedIndices.has(code)) {
                    if (this.selectedIndices.size <= 1) return;
                    this.selectedIndices.delete(code);
                } else {
                    this.selectedIndices.add(code);
                }

                this.renderIndexChips();
                this.updateComparisonChart();
                this.renderPerformanceMatrix();
            };
        });
    }

    // =========================================================================
    // 原有指数估值温度计逻辑 (保持完全兼容与稳定)
    // =========================================================================

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
