// QDII 基金模块 (纳斯达克100 & 标普500 场外 A类基金)
// 依赖: utils.js, api.js, styles.css

class QDIIController {
    constructor() {
        this.currentFilter = 'nasdaq100';
        this.rawFunds = [];
        this.benchmarks = {
            'NDX': { name: '纳斯达克100 原生指数', return_1y: 21.14 },
            'SPX': { name: '标普500 原生指数', return_1y: 16.48 }
        };
    }

    async loadData() {
        console.log('📊 加载 QDII 基金数据...');
        const container = document.getElementById('qdii-table-container');
        if (container) {
            container.innerHTML = '<div class="loading"><i data-lucide="loader-2" class="spin"></i> 数据加载中...</div>';
            if (window.lucide) lucide.createIcons();
        }

        try {
            const response = await api.getQDIIFunds();
            const data = response.data || response;

            if (data.status === 'warming_up') {
                utils.renderWarmingUp('qdii-table-container');
                this._retryCount = (this._retryCount || 0) + 1;
                if (this._retryCount <= 10 && !this._retryTimer) {
                    this._retryTimer = setTimeout(() => {
                        this._retryTimer = null;
                        this.loadData();
                    }, 3000);
                }
                return;
            }
            this._retryCount = 0;

            const funds = data.funds || (Array.isArray(data) ? data : []);

            if (!funds || !funds.length) {
                utils.renderError('qdii-table-container', data.message || data.error || '暂无 QDII 基金数据');
                return;
            }

            if (data.benchmarks) {
                this.benchmarks = data.benchmarks;
            }

            this.rawFunds = funds;
            this.renderTable();
            this.bindFilterButtons();
        } catch (error) {
            console.error('加载 QDII 基金数据失败:', error);
            utils.renderError('qdii-table-container', 'QDII 基金数据加载失败');
        }
    }

    bindFilterButtons() {
        const buttons = document.querySelectorAll('.qdii-filter-btn');
        buttons.forEach(btn => {
            btn.onclick = () => {
                buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentFilter = btn.dataset.filter || 'nasdaq100';
                this.renderTable();
            };
        });
    }

    renderTable() {
        const container = document.getElementById('qdii-table-container');
        if (!container) return;

        let filtered = this.rawFunds;
        let activeBenchmark = null;
        let indexName = '纳斯达克100';

        if (this.currentFilter === 'nasdaq100') {
            filtered = this.rawFunds.filter(f => f.index_code === 'NDX');
            activeBenchmark = this.benchmarks.NDX?.return_1y || 21.14;
            indexName = '纳斯达克100';
        } else if (this.currentFilter === 'sp500') {
            filtered = this.rawFunds.filter(f => f.index_code === 'SPX');
            activeBenchmark = this.benchmarks.SPX?.return_1y || 16.48;
            indexName = '标普500';
        } else if (this.currentFilter === 'active') {
            filtered = this.rawFunds.filter(f => f.index_code === 'ACTIVE' || f.type === 'active');
            activeBenchmark = null;
            indexName = '主动管理型';
        }

        if (!filtered.length) {
            utils.renderError('qdii-table-container', '该分类下暂无基金数据');
            return;
        }

        const isActiveTab = this.currentFilter === 'active';

        let rowsHtml = filtered.map((item, index) => {
            const rank = index + 1;
            const rankBadgeClass = rank === 1 ? 'rank-top1' : rank === 2 ? 'rank-top2' : rank === 3 ? 'rank-top3' : 'rank-other';

            const r1y = item.return_1y;
            const r1yClass = r1y > 0 ? 'text-up-us' : r1y < 0 ? 'text-down-us' : '';
            const r1yStr = r1y != null ? `${r1y > 0 ? '+' : ''}${utils.formatPercentage(r1y)}` : '--';

            // 对比原生指数差额
            let benchmarkGapStr = '--';
            if (r1y != null && activeBenchmark != null) {
                const gap = r1y - activeBenchmark;
                benchmarkGapStr = `${gap > 0 ? '+' : ''}${utils.formatPercentage(gap)}`;
            }

            // 资产配置比例
            const alloc = item.asset_allocation;
            let allocHtml = '<span style="color: var(--text-tertiary);">--</span>';

            if (alloc && alloc.stock_pct != null) {
                const stockPct = alloc.stock_pct.toFixed(1);
                const usPct = alloc.stock_us_pct != null ? alloc.stock_us_pct.toFixed(1) : null;
                const hkPct = alloc.stock_hk_pct != null ? alloc.stock_hk_pct.toFixed(1) : null;
                const cnPct = alloc.stock_cn_pct != null ? alloc.stock_cn_pct.toFixed(1) : null;
                const otherPct = alloc.stock_other_pct != null ? alloc.stock_other_pct.toFixed(1) : null;
                const cashPct = alloc.cash_pct != null ? alloc.cash_pct.toFixed(1) : '0.0';
                const bondPct = alloc.bond_pct != null ? alloc.bond_pct.toFixed(1) : '0.0';

                let subParts = [];
                const hasDetailed = (usPct != null && parseFloat(usPct) > 0) || (hkPct != null && parseFloat(hkPct) > 0) || (cnPct != null && parseFloat(cnPct) > 0) || (otherPct != null && parseFloat(otherPct) > 0);
                if (hasDetailed) {
                    if (usPct != null && parseFloat(usPct) > 0) subParts.push(`${usPct}% 美股`);
                    if (hkPct != null && parseFloat(hkPct) > 0) subParts.push(`${hkPct}% 港股`);
                    if (cnPct != null && parseFloat(cnPct) > 0) subParts.push(`${cnPct}% A股`);
                    if (otherPct != null && parseFloat(otherPct) > 0) subParts.push(`${otherPct}% 其他/日韩`);
                } else {
                    subParts.push(`${stockPct}% 股票`);
                }
                if (alloc.cash_pct > 0.1) subParts.push(`${cashPct}% 现金`);
                if (alloc.bond_pct > 0.5) subParts.push(`${bondPct}% 债券`);

                let allocLabel = subParts.join(' · ');

                // 严格遵循金融数据真实性：使用真实比例渲染色块，未披露/其他资产保留中性灰色背景轨道，容器左右边界 100% 对齐
                let barSegments = [];
                if (hasDetailed) {
                    if (usPct != null && parseFloat(usPct) > 0) barSegments.push({ cls: 'allocation-bar-us', val: parseFloat(usPct), title: `美股股票: ${usPct}%` });
                    if (hkPct != null && parseFloat(hkPct) > 0) barSegments.push({ cls: 'allocation-bar-hk', val: parseFloat(hkPct), title: `港股股票: ${hkPct}%` });
                    if (cnPct != null && parseFloat(cnPct) > 0) barSegments.push({ cls: 'allocation-bar-cn', val: parseFloat(cnPct), title: `A股股票: ${cnPct}%` });
                    if (otherPct != null && parseFloat(otherPct) > 0) barSegments.push({ cls: 'allocation-bar-other', val: parseFloat(otherPct), title: `日韩/其他股票: ${otherPct}%` });
                } else {
                    barSegments.push({ cls: 'allocation-bar-stock', val: parseFloat(stockPct), title: `股票: ${stockPct}%` });
                }
                if (alloc.cash_pct > 0.1) barSegments.push({ cls: 'allocation-bar-cash', val: parseFloat(cashPct), title: `现金: ${cashPct}%` });
                if (alloc.bond_pct > 0.5) barSegments.push({ cls: 'allocation-bar-bond', val: parseFloat(bondPct), title: `债券: ${bondPct}%` });

                const totalVal = barSegments.reduce((sum, s) => sum + s.val, 0);
                let barHtml = barSegments.map(s => `<div class="${s.cls}" style="width: ${s.val}%;" title="${s.title}"></div>`).join('');
                
                // 若存在未披露/其他杂项资产 (100% - totalVal)，用中性灰色条填充
                if (totalVal < 99.5) {
                    const unclassifiedPct = (100.0 - totalVal).toFixed(1);
                    barHtml += `<div class="allocation-bar-unclassified" style="width: ${unclassifiedPct}%;" title="其他/未披露资产: ${unclassifiedPct}%"></div>`;
                }

                allocHtml = `
                    <div class="allocation-cell" title="股票: ${stockPct}%${hasDetailed ? ' (美股 ' + (usPct || '0.0') + '%, 港股 ' + (hkPct || '0.0') + '%' + (cnPct ? ', A股 ' + cnPct + '%' : '') + (otherPct ? ', 其他/日韩 ' + otherPct + '%' : '') + ')' : ''}, 现金: ${cashPct}%">
                        <div class="allocation-text">
                            <span>${allocLabel}</span>
                        </div>
                        <div class="allocation-bar-track">
                            ${barHtml}
                        </div>
                    </div>
                `;
            }

            return `
                <tr>
                    <td class="col-rank"><span class="rank-badge ${rankBadgeClass}">${rank}</span></td>
                    <td class="col-name">
                        <div class="qdii-name-wrapper">
                            <span class="qdii-code-text">${item.code}</span>
                            <span class="qdii-name-text">${item.name}</span>
                            <div class="qdii-alloc-mobile">
                                ${allocHtml}
                            </div>
                        </div>
                    </td>
                    <td class="col-allocation">${allocHtml}</td>
                    <td class="col-fee font-mono">${item.fee_rate}</td>
                    <td class="col-return font-mono ${r1yClass}" style="font-weight: 700;">${r1yStr}</td>
                    ${!isActiveTab ? `
                        <td class="col-gap font-mono" style="color: var(--text-tertiary);">${benchmarkGapStr}</td>
                        <td class="col-tracking col-optional font-mono">${item.tracking_error || '--'}</td>
                    ` : ''}
                    <td class="col-date col-optional" style="color: var(--text-secondary);">${item.inception_date || '--'}</td>
                </tr>
            `;
        }).join('');

        const benchmarkNotice = activeBenchmark != null ? `
            <div style="padding: 10px 14px; margin-bottom: 12px; border-radius: 6px; background: var(--bg-body); border: 1px solid var(--border-light); font-size: clamp(0.72rem, 2.5vw, 0.78rem); color: var(--text-secondary); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                <div>
                    📌 <strong>【标的基准】${indexName} 原生指数近1年收益：<span class="text-up-us">+${utils.formatPercentage(activeBenchmark)}</span></strong>
                </div>
                <div style="color: var(--text-tertiary); font-size: 0.9em;">
                    对比差距为基金与原生指数收益差（含费率、汇率及仓位损耗）
                </div>
            </div>
        ` : (this.currentFilter === 'active' ? `
            <div style="padding: 10px 14px; margin-bottom: 12px; border-radius: 6px; background: var(--bg-body); border: 1px solid var(--border-light); font-size: clamp(0.72rem, 2.5vw, 0.78rem); color: var(--text-secondary); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                <div>
                    🎯 <strong>【主动型 QDII 精选】由基金经理团队进行全球多市场（美/港/A/日韩/台/印）主动选股与仓位管理</strong>
                </div>
                <div style="color: var(--text-tertiary); font-size: 0.9em;">
                    按近 1 年收益率降序排列 · 🔵 表示美股，🟣 表示港股，🔴 表示A股，🟠 表示日韩/台股等
                </div>
            </div>
        ` : '');

        container.innerHTML = `
            ${benchmarkNotice}
            <div class="table-wrapper">
                <table class="qdii-table">
                    <thead>
                        <tr>
                            <th class="col-rank">排名</th>
                            <th class="col-name">基金名称</th>
                            <th class="col-allocation">资产配置 / 仓位</th>
                            <th class="col-fee">综合费率</th>
                            <th class="col-return">近1年收益</th>
                            ${!isActiveTab ? `
                                <th class="col-gap">对标差距</th>
                                <th class="col-tracking col-optional">跟踪偏离度</th>
                            ` : ''}
                            <th class="col-date col-optional">成立时间</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
        `;
    }
}
