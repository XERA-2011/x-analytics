// QDII 基金模块 (纳斯达克100 & 标普500 场外 A类基金)
// 依赖: utils.js, api.js, styles.css

class QDIIController {
    constructor() {
        this.currentFilter = 'active';
        this.rawFunds = [];
        this.benchmarks = {
            'NDX': { name: '纳斯达克100 原生指数', return_1y: 21.14 },
            'SPX': { name: '标普500 原生指数', return_1y: 16.48 }
        };
        window.qdiiController = this;
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

        // 1. 桌面端宽屏大表格行渲染
        let desktopRowsHtml = filtered.map((item, index) => {
            const rank = index + 1;
            const rankBadgeClass = rank === 1 ? 'rank-top1' : rank === 2 ? 'rank-top2' : rank === 3 ? 'rank-top3' : 'rank-other';

            const r1y = item.return_1y;
            const r1yClass = r1y > 0 ? 'text-up-us' : r1y < 0 ? 'text-down-us' : '';
            const r1yStr = r1y != null ? `${r1y > 0 ? '+' : ''}${utils.formatPercentage(r1y)}` : '--';

            const mdd = item.max_drawdown;
            const mddStr = mdd != null ? `${utils.formatPercentage(mdd)}` : '--';

            const vol = item.volatility;
            const volStr = vol != null ? `${utils.formatPercentage(vol)}` : '--';

            let benchmarkGapStr = '--';
            if (r1y != null && activeBenchmark != null) {
                const gap = r1y - activeBenchmark;
                benchmarkGapStr = `${gap > 0 ? '+' : ''}${utils.formatPercentage(gap)}`;
            }

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
                    if (usPct != null && parseFloat(usPct) > 0) subParts.push(`<span class="alloc-text-item alloc-text-us">${usPct}% 美股</span>`);
                    if (hkPct != null && parseFloat(hkPct) > 0) subParts.push(`<span class="alloc-text-item alloc-text-hk">${hkPct}% 港股</span>`);
                    if (cnPct != null && parseFloat(cnPct) > 0) subParts.push(`<span class="alloc-text-item alloc-text-cn">${cnPct}% A股</span>`);
                    if (otherPct != null && parseFloat(otherPct) > 0) subParts.push(`<span class="alloc-text-item alloc-text-other">${otherPct}% 日韩/台股</span>`);
                } else {
                    subParts.push(`<span class="alloc-text-item alloc-text-stock">${stockPct}% 股票</span>`);
                }
                if (alloc.cash_pct > 0.1) subParts.push(`<span class="alloc-text-item alloc-text-cash">${cashPct}% 现金</span>`);
                if (alloc.bond_pct > 0.5) subParts.push(`<span class="alloc-text-item alloc-text-bond">${bondPct}% 债券</span>`);

                let barSegments = [];
                if (hasDetailed) {
                    if (usPct != null && parseFloat(usPct) > 0) barSegments.push({ cls: 'allocation-bar-us', val: parseFloat(usPct), title: `美股股票: ${usPct}%` });
                    if (hkPct != null && parseFloat(hkPct) > 0) barSegments.push({ cls: 'allocation-bar-hk', val: parseFloat(hkPct), title: `港股股票: ${hkPct}%` });
                    if (cnPct != null && parseFloat(cnPct) > 0) barSegments.push({ cls: 'allocation-bar-cn', val: parseFloat(cnPct), title: `A股股票: ${cnPct}%` });
                    if (otherPct != null && parseFloat(otherPct) > 0) barSegments.push({ cls: 'allocation-bar-other', val: parseFloat(otherPct), title: `日韩/台股: ${otherPct}%` });
                } else {
                    barSegments.push({ cls: 'allocation-bar-stock', val: parseFloat(stockPct), title: `股票: ${stockPct}%` });
                }
                if (alloc.cash_pct > 0.1) barSegments.push({ cls: 'allocation-bar-cash', val: parseFloat(cashPct), title: `现金: ${cashPct}%` });
                if (alloc.bond_pct > 0.5) barSegments.push({ cls: 'allocation-bar-bond', val: parseFloat(bondPct), title: `债券: ${bondPct}%` });

                const totalVal = barSegments.reduce((sum, s) => sum + s.val, 0);
                let barHtml = barSegments.map(s => `<div class="${s.cls}" style="flex: 0 0 ${s.val}%; width: ${s.val}%;" title="${s.title}"></div>`).join('');
                
                if (totalVal < 99.5) {
                    const unclassifiedPct = (100.0 - totalVal).toFixed(1);
                    barHtml += `<div class="allocation-bar-unclassified" style="flex: 0 0 ${unclassifiedPct}%; width: ${unclassifiedPct}%;" title="其它资产: ${unclassifiedPct}%"></div>`;
                    subParts.push(`<span class="alloc-text-item alloc-text-unclassified">${unclassifiedPct}% 其它</span>`);
                }

                let allocLabel = subParts.join('<span class="alloc-sep">·</span>');
                let warningHtml = item.allocation_estimated ? `<span class="alloc-warning-wrapper" title="提示：二季报官方国家/地区明细未完全披露，各地区占比为基于底层资产或历史持仓的估算参考值" style="cursor: help; display: inline-flex; align-items: center; margin-left: 2px;"><i data-lucide="alert-circle" style="width: 12px; height: 12px; color: var(--accent-red); vertical-align: middle;"></i></span>` : '';

                let tooltipParts = [];
                tooltipParts.push(`股票: ${stockPct}%${hasDetailed ? ' (美股 ' + (usPct || '0.0') + '%, 港股 ' + (hkPct || '0.0') + '%' + (cnPct ? ', A股 ' + cnPct + '%' : '') + (otherPct ? ', 日韩/台股 ' + otherPct + '%' : '') + ')' : ''}`);
                if (alloc.cash_pct > 0.1) tooltipParts.push(`现金: ${cashPct}%`);
                if (alloc.bond_pct > 0.5) tooltipParts.push(`债券: ${bondPct}%`);
                if (totalVal < 99.5) {
                    const unclassifiedPct = (100.0 - totalVal).toFixed(1);
                    tooltipParts.push(`其它: ${unclassifiedPct}%`);
                }
                const cellTooltipTitle = tooltipParts.join(', ');

                allocHtml = `
                    <div class="allocation-cell" title="${cellTooltipTitle}">
                        <div class="allocation-text">
                            ${allocLabel}${warningHtml}
                        </div>
                        <div class="allocation-bar-track">
                            ${barHtml}
                        </div>
                    </div>
                `;
            }

            const tagHtml = item.tag ? `<span class="fund-tag" style="background: rgba(115,115,115,0.08); color: var(--text-secondary); font-size: 10px; padding: 1px 4px; border-radius: 3px; font-weight: 600; margin-left: 6px; border: 1px solid rgba(115,115,115,0.25); display: inline-block; vertical-align: middle; transform: translateY(-1.5px);">${item.tag}</span>` : '';

            const buyStatus = item.buy_status || '开放申购';
            let statusText = '开放';
            let statusClass = 'status-open';
            if (buyStatus === '限大额') {
                statusText = '限额';
                statusClass = 'status-limit';
            } else if (buyStatus.includes('暂停')) {
                statusText = '暂停';
                statusClass = 'status-paused';
            }

            return `
                <tr>
                    <td class="col-rank"><span class="rank-badge ${rankBadgeClass}">${rank}</span></td>
                    <td class="col-name qdii-clickable" data-code="${item.code}" data-name="${item.name}" title="点击查看 ${item.name} 前十大重仓股">
                        <div class="qdii-name-wrapper">
                            <div style="display: flex; align-items: center; gap: 4px; flex-wrap: wrap;">
                                <span class="qdii-code-text">${item.code}</span>
                                ${tagHtml}
                            </div>
                            <span class="qdii-name-text" style="color: var(--primary); font-weight: 600;">${item.name}</span>
                        </div>
                    </td>
                    <td class="col-allocation qdii-clickable" data-code="${item.code}" data-name="${item.name}" title="点击查看 ${item.name} 前十大重仓股">${allocHtml}</td>
                    <td class="col-return font-mono ${r1yClass}" style="font-weight: 700;">${r1yStr}</td>
                    <td class="col-drawdown font-mono" style="color: var(--text-secondary);">${mddStr}</td>
                    <td class="col-volatility font-mono" style="color: var(--text-secondary);">${volStr}</td>
                    <td class="col-fee font-mono">${item.fee_rate}</td>
                    <td class="col-scale font-mono" style="color: var(--text-secondary);">${item.scale || '--'}</td>
                    <td class="col-status"><span class="status-badge ${statusClass}">${statusText}</span></td>
                    ${!isActiveTab ? `
                        <td class="col-gap font-mono" style="color: var(--text-tertiary);">${benchmarkGapStr}</td>
                        <td class="col-tracking font-mono">${item.tracking_error || '--'}</td>
                    ` : ''}
                    <td class="col-date" style="color: var(--text-secondary);">${item.inception_date || '--'}</td>
                </tr>
            `;
        }).join('');

        // 2. 移动端现代金融卡片流渲染 (方案 A: 4列数据网格 + 全宽资产配置条)
        let mobileCardsHtml = filtered.map((item, index) => {
            const rank = index + 1;
            const rankBadgeClass = rank === 1 ? 'rank-top1' : rank === 2 ? 'rank-top2' : rank === 3 ? 'rank-top3' : 'rank-other';

            const r1y = item.return_1y;
            const r1yClass = r1y > 0 ? 'text-up-us' : r1y < 0 ? 'text-down-us' : '';
            const r1yStr = r1y != null ? `${r1y > 0 ? '+' : ''}${utils.formatPercentage(r1y)}` : '--';

            const mdd = item.max_drawdown;
            const mddStr = mdd != null ? `${utils.formatPercentage(mdd)}` : '--';

            const vol = item.volatility;
            const volStr = vol != null ? `${utils.formatPercentage(vol)}` : '--';

            const scaleShort = item.scale ? item.scale.replace('亿元', '亿') : '--';

            const buyStatus = item.buy_status || '开放申购';
            let statusText = '开放';
            let statusClass = 'status-open';
            if (buyStatus === '限大额') {
                statusText = '限额';
                statusClass = 'status-limit';
            } else if (buyStatus.includes('暂停')) {
                statusText = '暂停';
                statusClass = 'status-paused';
            }

            const tagHtml = item.tag ? `<span class="qdii-mcard-tag">${item.tag}</span>` : '';

            // 资产配置
            const alloc = item.asset_allocation;
            let allocMobileHtml = '';
            if (alloc && alloc.stock_pct != null) {
                const usPct = alloc.stock_us_pct != null ? alloc.stock_us_pct.toFixed(1) : null;
                const hkPct = alloc.stock_hk_pct != null ? alloc.stock_hk_pct.toFixed(1) : null;
                const cnPct = alloc.stock_cn_pct != null ? alloc.stock_cn_pct.toFixed(1) : null;
                const otherPct = alloc.stock_other_pct != null ? alloc.stock_other_pct.toFixed(1) : null;
                const stockPct = alloc.stock_pct.toFixed(1);
                const cashPct = alloc.cash_pct != null ? alloc.cash_pct.toFixed(1) : '0.0';
                const bondPct = alloc.bond_pct != null ? alloc.bond_pct.toFixed(1) : '0.0';

                let subParts = [];
                const hasDetailed = (usPct != null && parseFloat(usPct) > 0) || (hkPct != null && parseFloat(hkPct) > 0) || (cnPct != null && parseFloat(cnPct) > 0) || (otherPct != null && parseFloat(otherPct) > 0);
                if (hasDetailed) {
                    if (usPct != null && parseFloat(usPct) > 0) subParts.push(`<span class="alloc-text-item alloc-text-us">${usPct}% 美股</span>`);
                    if (hkPct != null && parseFloat(hkPct) > 0) subParts.push(`<span class="alloc-text-item alloc-text-hk">${hkPct}% 港股</span>`);
                    if (cnPct != null && parseFloat(cnPct) > 0) subParts.push(`<span class="alloc-text-item alloc-text-cn">${cnPct}% A股</span>`);
                    if (otherPct != null && parseFloat(otherPct) > 0) subParts.push(`<span class="alloc-text-item alloc-text-other">${otherPct}% 日韩/台股</span>`);
                } else {
                    subParts.push(`<span class="alloc-text-item alloc-text-stock">${stockPct}% 股票</span>`);
                }
                if (alloc.cash_pct > 0.1) subParts.push(`<span class="alloc-text-item alloc-text-cash">${cashPct}% 现金</span>`);
                if (alloc.bond_pct > 0.5) subParts.push(`<span class="alloc-text-item alloc-text-bond">${bondPct}% 债券</span>`);

                let barSegments = [];
                if (hasDetailed) {
                    if (usPct != null && parseFloat(usPct) > 0) barSegments.push({ cls: 'allocation-bar-us', val: parseFloat(usPct) });
                    if (hkPct != null && parseFloat(hkPct) > 0) barSegments.push({ cls: 'allocation-bar-hk', val: parseFloat(hkPct) });
                    if (cnPct != null && parseFloat(cnPct) > 0) barSegments.push({ cls: 'allocation-bar-cn', val: parseFloat(cnPct) });
                    if (otherPct != null && parseFloat(otherPct) > 0) barSegments.push({ cls: 'allocation-bar-other', val: parseFloat(otherPct) });
                } else {
                    barSegments.push({ cls: 'allocation-bar-stock', val: parseFloat(stockPct) });
                }
                if (alloc.cash_pct > 0.1) barSegments.push({ cls: 'allocation-bar-cash', val: parseFloat(cashPct) });
                if (alloc.bond_pct > 0.5) barSegments.push({ cls: 'allocation-bar-bond', val: parseFloat(bondPct) });

                const totalVal = barSegments.reduce((sum, s) => sum + s.val, 0);
                let barHtml = barSegments.map(s => `<div class="${s.cls}" style="flex: 0 0 ${s.val}%; width: ${s.val}%;"></div>`).join('');
                if (totalVal < 99.5) {
                    const unclassifiedPct = (100.0 - totalVal).toFixed(1);
                    barHtml += `<div class="allocation-bar-unclassified" style="flex: 0 0 ${unclassifiedPct}%; width: ${unclassifiedPct}%;"></div>`;
                    subParts.push(`<span class="alloc-text-item alloc-text-unclassified">${unclassifiedPct}% 其它</span>`);
                }

                let allocLabel = subParts.join('<span class="alloc-sep">·</span>');
                let warningHtml = item.allocation_estimated ? `<span class="alloc-warning-wrapper" title="估算参考值" style="margin-left: 2px;"><i data-lucide="alert-circle" style="width: 10px; height: 10px; color: var(--accent-red); vertical-align: middle;"></i></span>` : '';

                allocMobileHtml = `
                    <div class="qdii-mcard-alloc-box">
                        <div class="allocation-bar-track qdii-mcard-bar-track">
                            ${barHtml}
                        </div>
                    </div>
                `;
            }

            return `
                <div class="qdii-mobile-card qdii-clickable" data-code="${item.code}" data-name="${item.name}" title="点击查看 ${item.name} 前十大重仓股">
                    <div class="qdii-mcard-top">
                        <div class="qdii-mcard-rank-col">
                            <span class="rank-badge ${rankBadgeClass}">${rank}</span>
                        </div>
                        <div class="qdii-mcard-info-col">
                            <div class="qdii-mcard-title-line">
                                <span class="qdii-mcard-name">${item.name}</span>
                            </div>
                            <div class="qdii-mcard-meta-line">
                                <span class="qdii-mcard-code font-mono">${item.code}</span>
                                ${tagHtml}
                            </div>
                        </div>
                        <div class="qdii-mcard-status-col">
                            <span class="status-badge ${statusClass}">${statusText}</span>
                        </div>
                    </div>
                    <div class="qdii-mcard-grid">
                        <div class="qdii-mcard-metric-cell metric-cell-return">
                            <div class="qdii-mcard-val font-mono ${r1yClass}" style="font-weight: 700;">${r1yStr}</div>
                            <div class="qdii-mcard-lbl">近1年收益</div>
                        </div>
                        <div class="qdii-mcard-metric-cell">
                            <div class="qdii-mcard-val font-mono">${mddStr}</div>
                            <div class="qdii-mcard-lbl">近1年回撤</div>
                        </div>
                        <div class="qdii-mcard-metric-cell">
                            <div class="qdii-mcard-val font-mono">${volStr}</div>
                            <div class="qdii-mcard-lbl">年化波动率</div>
                        </div>
                        <div class="qdii-mcard-metric-cell metric-cell-scale">
                            <div class="qdii-mcard-val font-mono">${scaleShort}</div>
                            <div class="qdii-mcard-lbl">费率 ${item.fee_rate || '--'}</div>
                        </div>
                    </div>
                    ${allocMobileHtml}
                </div>
            `;
        }).join('');

        const benchmarkNotice = activeBenchmark != null ? `
            <div style="padding: 10px 14px; margin-bottom: 12px; border-radius: 6px; background: var(--bg-body); border: 1px solid var(--border-light); font-size: clamp(0.72rem, 2.5vw, 0.78rem); color: var(--text-secondary); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                <div>
                    📌 <strong>【标的基准】${indexName} 原生指数近1年收益：<span class="text-up-us">+${utils.formatPercentage(activeBenchmark)}</span></strong>
                </div>
                <div class="qdii-legend-group">
                    <span class="qdii-legend-tag tag-us">美股</span>
                    <span class="qdii-legend-tag tag-hk">港股</span>
                    <span class="qdii-legend-tag tag-cn">A股</span>
                    <span class="qdii-legend-tag tag-other">日韩/台股</span>
                    <span class="qdii-legend-tag tag-cash">现金</span>
                    <span class="qdii-legend-tag tag-bond">债券</span>
                    <span class="qdii-legend-tag tag-unclassified">其它</span>
                </div>
            </div>
        ` : (this.currentFilter === 'active' ? `
            <div style="padding: 10px 14px; margin-bottom: 12px; border-radius: 6px; background: var(--bg-body); border: 1px solid var(--border-light); font-size: clamp(0.72rem, 2.5vw, 0.78rem); color: var(--text-secondary); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                <div>
                    🎯 <strong>【主动型 QDII】全球市场动态主动配置</strong>
                </div>
                <div class="qdii-legend-group">
                    <span class="qdii-legend-tag tag-us">美股</span>
                    <span class="qdii-legend-tag tag-hk">港股</span>
                    <span class="qdii-legend-tag tag-cn">A股</span>
                    <span class="qdii-legend-tag tag-other">日韩/台股</span>
                    <span class="qdii-legend-tag tag-cash">现金</span>
                    <span class="qdii-legend-tag tag-bond">债券</span>
                    <span class="qdii-legend-tag tag-unclassified">其它</span>
                </div>
            </div>
        ` : '');

        container.innerHTML = `
            ${benchmarkNotice}
            <!-- 桌面端宽屏大表格 -->
            <div class="table-wrapper qdii-desktop-only">
                <table class="qdii-table">
                    <thead>
                        <tr>
                            <th class="col-rank">排名</th>
                            <th class="col-name">基金名称</th>
                            <th class="col-allocation">资产配置 / 仓位</th>
                            <th class="col-return">近1年收益</th>
                            <th class="col-drawdown">近1年回撤</th>
                            <th class="col-volatility">年化波动率</th>
                            <th class="col-fee">综合费率</th>
                            <th class="col-scale">资产规模</th>
                            <th class="col-status">状态</th>
                            ${!isActiveTab ? `
                                <th class="col-gap">对标差距</th>
                                <th class="col-tracking">跟踪偏离度</th>
                            ` : ''}
                            <th class="col-date">成立时间</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${desktopRowsHtml}
                    </tbody>
                </table>
            </div>

            <!-- 移动端现代金融卡片流 (方案 A) -->
            <div class="qdii-mobile-cards-wrapper qdii-mobile-only">
                ${mobileCardsHtml}
            </div>
        `;

        // 绑定重仓持仓点击事件
        container.querySelectorAll('.qdii-clickable').forEach(el => {
            el.onclick = (e) => {
                const code = el.dataset.code;
                const name = el.dataset.name;
                if (code && name) {
                    this.openHoldingsModal(code, name);
                }
            };
        });

        // 渲染 Lucide 图标
        if (window.lucide) lucide.createIcons();
    }

    async openHoldingsModal(code, name) {
        let overlay = document.getElementById('qdii-holdings-modal');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'qdii-holdings-modal';
            overlay.className = 'qdii-modal-overlay';
            document.body.appendChild(overlay);

            overlay.onclick = (e) => {
                if (e.target === overlay) this.closeHoldingsModal();
            };

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && overlay.classList.contains('active')) {
                    this.closeHoldingsModal();
                }
            });
        }

        overlay.innerHTML = `
            <div class="qdii-modal-card">
                <div class="qdii-modal-header">
                    <h3 class="qdii-modal-title">
                        📊 ${name} <span style="font-size: 0.8rem; font-weight: normal; color: var(--text-tertiary);">(${code})</span>
                    </h3>
                    <button class="qdii-modal-close" aria-label="关闭">&times;</button>
                </div>
                <div class="qdii-modal-body" id="qdii-modal-body-content">
                    <div class="loading"><i data-lucide="loader-2" class="spin"></i> 正在获取最新重仓持仓明细...</div>
                </div>
            </div>
        `;
        const closeBtn = overlay.querySelector('.qdii-modal-close');
        if (closeBtn) {
            closeBtn.onclick = () => this.closeHoldingsModal();
        }
        overlay.classList.add('active');
        if (window.lucide) lucide.createIcons();

        try {
            const res = await api.getQDIIHoldings(code);
            const data = res.data || res;

            if (data.status === 'warming_up') {
                const bodyEl = overlay.querySelector('.qdii-modal-body');
                if (bodyEl) bodyEl.innerHTML = '<div class="loading">数据计算中，请稍后刷新...</div>';
                return;
            }

            const holdings = data.holdings || [];
            const reportDate = data.report_date || '最新季报';

            const bodyEl = overlay.querySelector('.qdii-modal-body');
            if (!bodyEl) return;

            if (holdings.length === 0) {
                bodyEl.innerHTML = `<div style="text-align: center; color: var(--text-tertiary); padding: 24px;">暂无该基金的前十大重仓披露信息</div>`;
                return;
            }

            const rowsHtml = holdings.map(h => {
                const rawRatio = h.ratio_val || 0;
                const barWidth = rawRatio > 0 ? Math.max(0.5, Math.min(100, rawRatio)) : 0;
                
                // 渲染持仓证券类型徽章
                let badgeHtml = '';
                if (h.stock_type) {
                    let bgColor = 'rgba(115, 115, 115, 0.1)';
                    let textColor = 'var(--text-secondary)';
                    
                    if (h.stock_type === 'A股') {
                        bgColor = 'rgba(239, 68, 68, 0.1)';
                        textColor = 'var(--accent-red)';
                    } else if (h.stock_type === '美股') {
                        bgColor = 'rgba(59, 130, 246, 0.1)';
                        textColor = 'var(--accent-blue)';
                    } else if (h.stock_type === '港股') {
                        bgColor = 'rgba(34, 197, 94, 0.1)';
                        textColor = 'var(--accent-green)';
                    } else if (h.stock_type === '其他' || h.stock_type === '现金') {
                        bgColor = 'rgba(115, 115, 115, 0.1)';
                        textColor = 'var(--text-secondary)';
                    }
                    
                    badgeHtml = `<span style="font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; font-weight: bold; background: ${bgColor}; color: ${textColor}; display: inline-flex; align-items: center; justify-content: center; line-height: 1; vertical-align: middle;">${h.stock_type}</span>`;
                }

                // 计算较上季变化渲染内容
                let changeHtml = '';
                if (h.change_status === 'new') {
                    changeHtml = `<span style="font-size: 0.68rem; padding: 2px 6px; border-radius: 4px; font-weight: bold; background: rgba(59, 130, 246, 0.1); color: var(--accent-blue); border: 1px solid rgba(59, 130, 246, 0.25); display: inline-flex; align-items: center; gap: 2px;"><i data-lucide="sparkles" style="width: 10px; height: 10px;"></i>新进</span>`;
                } else if (h.change_status === 'up') {
                    changeHtml = `<span style="color: var(--accent-green); font-weight: 700; font-family: monospace; font-size: 0.8rem; display: inline-flex; align-items: center; gap: 2px;">▲ ${h.change_pct}</span>`;
                } else if (h.change_status === 'down') {
                    changeHtml = `<span style="color: var(--accent-red); font-weight: 700; font-family: monospace; font-size: 0.8rem; display: inline-flex; align-items: center; gap: 2px;">▼ ${h.change_pct}</span>`;
                } else {
                    changeHtml = `<span style="color: var(--text-tertiary); font-family: monospace; font-size: 0.8rem;">0.00%</span>`;
                }

                return `
                    <tr>
                        <td style="width: 36px; text-align: center; font-weight: bold; color: var(--text-secondary);">${h.rank}</td>
                        <td style="font-weight: 600;">
                            <div>${h.stock_name}</div>
                            <div style="font-size: 0.72rem; color: var(--text-tertiary); font-family: monospace; margin-top: 2px; display: flex; align-items: center; gap: 6px;">
                                <span>${h.stock_code}</span>
                                ${badgeHtml}
                            </div>
                        </td>
                        <td style="width: 25%; text-align: right; font-weight: 700; font-family: monospace;">
                            ${h.ratio_pct}
                        </td>
                        <td style="width: 25%; text-align: right; font-weight: 600;">
                            ${changeHtml}
                        </td>
                    </tr>
                `;
            }).join('');

            // 构建联接穿透信息提示
            let penetrationHtml = '';
            if (data.is_penetrated && data.target_code) {
                penetrationHtml = `
                    <div style="background: rgba(59, 130, 246, 0.06); border: 1px solid rgba(59, 130, 246, 0.15); border-radius: 6px; padding: 8px 12px; font-size: 0.76rem; color: var(--accent-blue); margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
                        <i data-lucide="link" style="width: 14px; height: 14px; flex-shrink: 0;"></i>
                        <span>当前持仓已自动穿透至底层联接的 ETF (<strong>${data.target_code}</strong>) 获取真实持仓</span>
                    </div>
                `;
            }

            // 构建已退出/清仓标的列表提示
            let exitedHtml = '';
            const exited = data.exited_holdings || [];
            if (exited.length > 0) {
                const listHtml = exited.map(ex => {
                    return `<span style="background: var(--bg-secondary); border: 1px solid var(--border-light); padding: 2px 8px; border-radius: 4px; display: inline-flex; align-items: center; gap: 4px; font-weight: 500; font-size: 0.7rem; color: var(--text-secondary); margin-right: 6px; margin-bottom: 6px;">
                        <span>🚪 ${ex.stock_name}</span>
                        <span style="font-size: 0.65rem; color: var(--text-tertiary); font-family: monospace;">(${ex.previous_ratio_pct})</span>
                    </span>`;
                }).join('');
                
                exitedHtml = `
                    <div class="qdii-exited-holdings-container" style="margin-top: 16px; padding-top: 14px; border-top: 1px dashed var(--border-light);">
                        <div style="font-size: 0.72rem; font-weight: 600; color: var(--text-tertiary); margin-bottom: 8px; display: flex; align-items: center; gap: 4px;">
                            <i data-lucide="log-out" style="width: 12px; height: 12px;"></i>
                            <span>上季重仓已退出/清仓 (前十)</span>
                        </div>
                        <div style="display: flex; flex-wrap: wrap;">
                            ${listHtml}
                        </div>
                    </div>
                `;
            }

            const totalCount = data.total_count || holdings.length;
            const top10Concentration = data.top10_concentration != null ? `${data.top10_concentration}%` : '--%';

            const fundItem = (this.rawFunds || []).find(f => f.code === code) || {};
            const mdd = fundItem.max_drawdown != null ? `${utils.formatPercentage(fundItem.max_drawdown)}` : '--';
            const vol = fundItem.volatility != null ? `${utils.formatPercentage(fundItem.volatility)}` : '--';
            const sharpe = fundItem.sharpe != null ? `${fundItem.sharpe.toFixed(2)}` : '--';
            const r1y = fundItem.return_1y != null ? `${fundItem.return_1y > 0 ? '+' : ''}${utils.formatPercentage(fundItem.return_1y)}` : '--';

            bodyEl.innerHTML = `
                ${penetrationHtml}
                <div class="qdii-holding-meta" style="flex-wrap: wrap; gap: 8px 14px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px dashed var(--border-light); font-size: 0.76rem;">
                    <span>📅 截止日期：<strong>${reportDate}</strong></span>
                    <span>📦 总持仓：<strong>${totalCount} 只</strong></span>
                    <span>🎯 前十占比：<strong>${top10Concentration}</strong></span>
                    <span>📈 近1年收益：<strong class="${fundItem.return_1y > 0 ? 'text-up-us' : ''}">${r1y}</strong></span>
                    <span>📉 近1年回撤：<strong>${mdd}</strong></span>
                    <span>⚡ 年化波动率：<strong>${vol}</strong></span>
                    <span>📐 夏普比率：<strong>${sharpe}</strong></span>
                </div>
                <table class="qdii-holding-table">
                    <thead>
                        <tr>
                            <th style="width: 36px; text-align: center;">#</th>
                            <th>股票名称 / 代码</th>
                            <th style="width: 25%; text-align: right;">占净值比例</th>
                            <th style="width: 25%; text-align: right;">较上季变化</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rowsHtml}
                    </tbody>
                </table>
                ${exitedHtml}
            `;
            if (window.lucide) lucide.createIcons();
        } catch (err) {
            console.error('获取持仓明细失败:', err);
            utils.renderError('qdii-modal-body-content', '获取持仓明细失败，请稍后重试');
        }
    }

    closeHoldingsModal() {
        const overlay = document.getElementById('qdii-holdings-modal');
        if (overlay) overlay.classList.remove('active');
    }
}

