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

            const urlParams = new URLSearchParams(window.location.search);
            const initialFilter = urlParams.get('filter') || urlParams.get('subtab');
            if (initialFilter && ['active', 'nasdaq100', 'sp500'].includes(initialFilter)) {
                this.currentFilter = initialFilter;
                const buttons = document.querySelectorAll('.qdii-filter-btn');
                buttons.forEach(b => {
                    b.classList.toggle('active', b.dataset.filter === initialFilter);
                });
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
                this.currentFilter = btn.dataset.filter || 'active';
                const url = new URL(window.location.href);
                if (this.currentFilter === 'active') {
                    url.searchParams.delete('filter');
                    url.searchParams.delete('subtab');
                } else {
                    url.searchParams.set('filter', this.currentFilter);
                }
                window.history.replaceState({}, '', url.toString());
                this.renderTable();
            };
        });
    }

    _calcNormalizedAllocation(item) {
        const alloc = item.asset_allocation;
        if (!alloc || alloc.stock_pct == null) return null;

        const usRaw = alloc.stock_us_pct != null ? alloc.stock_us_pct : null;
        const hkRaw = alloc.stock_hk_pct != null ? alloc.stock_hk_pct : null;
        const cnRaw = alloc.stock_cn_pct != null ? alloc.stock_cn_pct : null;
        const otherRaw = alloc.stock_other_pct != null ? alloc.stock_other_pct : null;
        const stockRaw = alloc.stock_pct != null ? alloc.stock_pct : null;
        const cashRaw = alloc.cash_pct != null ? alloc.cash_pct : 0;
        const bondRaw = alloc.bond_pct != null ? alloc.bond_pct : 0;

        const hasDetailed = (usRaw != null && parseFloat(usRaw) > 0) || 
                            (hkRaw != null && parseFloat(hkRaw) > 0) || 
                            (cnRaw != null && parseFloat(cnRaw) > 0) || 
                            (otherRaw != null && parseFloat(otherRaw) > 0);

        const isJapanFund = (item.name && item.name.includes('日本')) || (item.tag && item.tag.includes('日本'));
        const otherRegionText = isJapanFund ? '日股' : '日韩/台股';

        let segments = [];
        if (hasDetailed) {
            if (usRaw != null && parseFloat(usRaw) > 0) {
                segments.push({ key: 'us', name: '美股', rawVal: parseFloat(usRaw), cls: 'allocation-bar-us', textCls: 'alloc-text-us' });
            }
            if (hkRaw != null && parseFloat(hkRaw) > 0) {
                segments.push({ key: 'hk', name: '港股', rawVal: parseFloat(hkRaw), cls: 'allocation-bar-hk', textCls: 'alloc-text-hk' });
            }
            if (cnRaw != null && parseFloat(cnRaw) > 0) {
                segments.push({ key: 'cn', name: 'A股', rawVal: parseFloat(cnRaw), cls: 'allocation-bar-cn', textCls: 'alloc-text-cn' });
            }
            if (otherRaw != null && parseFloat(otherRaw) > 0) {
                segments.push({ key: 'other', name: otherRegionText, rawVal: parseFloat(otherRaw), cls: 'allocation-bar-other', textCls: 'alloc-text-other' });
            }
        } else {
            if (stockRaw != null && parseFloat(stockRaw) > 0) {
                segments.push({ key: 'stock', name: '股票', rawVal: parseFloat(stockRaw), cls: 'allocation-bar-stock', textCls: 'alloc-text-stock' });
            }
        }

        if (cashRaw != null && parseFloat(cashRaw) > 0.05) {
            segments.push({ key: 'cash', name: '现金', rawVal: parseFloat(cashRaw), cls: 'allocation-bar-cash', textCls: 'alloc-text-cash' });
        }
        if (bondRaw != null && parseFloat(bondRaw) > 0.05) {
            segments.push({ key: 'bond', name: '债券', rawVal: parseFloat(bondRaw), cls: 'allocation-bar-bond', textCls: 'alloc-text-bond' });
        }

        const totalVal = segments.reduce((sum, s) => sum + s.rawVal, 0);
        if (totalVal <= 0) return null;

        // 严格按比例归一化为 100.0%
        let sumNorm = 0;
        segments.forEach((s, idx) => {
            if (idx === segments.length - 1) {
                s.normVal = Math.max(0.1, Math.round((100.0 - sumNorm) * 10) / 10);
            } else {
                s.normVal = Math.round(((s.rawVal / totalVal) * 100) * 10) / 10;
                sumNorm += s.normVal;
            }
            s.pctStr = s.normVal.toFixed(1);
            s.rawStr = s.rawVal.toFixed(1);
        });

        // 构造悬浮详情 Tooltip (展示归一化后的资产结构和官方季报原始净值口径)
        const normSummary = segments.map(s => `${s.pctStr}% ${s.name}`).join(' · ');
        const rawSummary = segments.map(s => `${s.name} ${s.rawStr}%`).join(', ');
        const reportNotice = totalVal > 100.5
            ? `(季报占净比合计 ${totalVal.toFixed(1)}%，因含待清算款/应付款等净资产口径略大于100%)`
            : totalVal < 98.5
            ? `(季报占净比合计 ${totalVal.toFixed(1)}%，其余为存出保证金及应收清算款项)`
            : `(季报占净比合计 ${totalVal.toFixed(1)}%)`;
        
        const tooltip = `资产配置结构: ${normSummary}\n官方季报口径: ${rawSummary} ${reportNotice}`;

        return {
            segments,
            normSummary,
            tooltip,
            totalVal
        };
    }

    renderTable() {
        const container = document.getElementById('qdii-table-container');
        if (!container) return;

        let filtered = this.rawFunds;
        let activeBenchmark = null;
        let indexName = '纳斯达克100';

        if (this.currentFilter === 'nasdaq100') {
            filtered = this.rawFunds.filter(f => f.type !== 'active' && f.index_code === 'NDX');
            activeBenchmark = this.benchmarks.NDX?.return_1y || 24.69;
            indexName = '纳斯达克';
        } else if (this.currentFilter === 'sp500') {
            filtered = this.rawFunds.filter(f => f.type !== 'active' && (f.index_code && f.index_code.startsWith('SPX')));
            activeBenchmark = this.benchmarks.SPX?.return_1y || 19.23;
            indexName = '标普500';
        } else if (this.currentFilter === 'active') {
            filtered = this.rawFunds.filter(f => f.index_code === 'ACTIVE' || f.type === 'active' || f.index_code === 'KR_CN');
            activeBenchmark = null;
            indexName = '主动管理型';
        }

        if (!filtered.length) {
            utils.renderError('qdii-table-container', '该分类下暂无基金数据');
            return;
        }

        // 1. 桌面端宽屏大表格行渲染
        let desktopRowsHtml = filtered.map((item, index) => {
            const rank = index + 1;
            const rankBadgeClass = rank === 1 ? 'rank-top1' : rank === 2 ? 'rank-top2' : rank === 3 ? 'rank-top3' : 'rank-other';

            const r1y = item.return_1y;
            const r1yClass = typeof APP_CONFIG !== 'undefined' ? APP_CONFIG.getChangeClass(r1y) : (r1y > 0 ? 'text-up' : r1y < 0 ? 'text-down' : '');
            const r1yStr = r1y != null ? `${r1y > 0 ? '+' : ''}${utils.formatPercentage(r1y)}` : '--';

            const r3y = item.return_3y;
            const r3yClass = r3y != null ? (typeof APP_CONFIG !== 'undefined' ? APP_CONFIG.getChangeClass(r3y) : (r3y > 0 ? 'text-up' : r3y < 0 ? 'text-down' : '')) : '';
            const r3yStr = r3y != null ? `${r3y > 0 ? '+' : ''}${utils.formatPercentage(r3y)}` : '--';

            const mdd = item.max_drawdown;
            const mddStr = mdd != null ? `${utils.formatPercentage(mdd)}` : '--';

            const vol = item.volatility;
            const volStr = vol != null ? `${utils.formatPercentage(vol)}` : '--';

            const allocInfo = this._calcNormalizedAllocation(item);
            let allocHtml = '<span style="color: var(--text-tertiary);">--</span>';

            if (allocInfo && allocInfo.segments.length > 0) {
                const subParts = allocInfo.segments.map(s => 
                    `<span class="alloc-text-item ${s.textCls}">${s.pctStr}% ${s.name}</span>`
                );
                const allocLabel = subParts.join('<span class="alloc-sep">·</span>');

                const barHtml = allocInfo.segments.map(s => {
                    const w = s.pctStr;
                    return `<div class="${s.cls}" style="flex: 0 0 ${w}%; width: ${w}%;" title="${s.name}: ${w}% (季报原值: ${s.rawStr}%)"></div>`;
                }).join('');

                allocHtml = `
                    <div class="allocation-cell" title="${allocInfo.tooltip}">
                        <div class="allocation-text">
                            ${allocLabel}
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
                    <td class="col-return">
                        <div class="qdii-return-cell">
                            <div class="qdii-return-row">
                                <span class="qdii-return-lbl">近一年</span>
                                <span class="font-mono ${r1yClass}" style="font-weight: 700;">${r1yStr}</span>
                            </div>
                            <div class="qdii-return-row">
                                <span class="qdii-return-lbl">近三年</span>
                                <span class="font-mono ${r3yClass}" style="font-weight: ${r3y != null ? '700' : '400'}; ${r3y == null ? 'color: var(--text-tertiary);' : ''}">${r3yStr}</span>
                            </div>
                        </div>
                    </td>
                    <td class="col-drawdown font-mono" style="color: var(--text-secondary);">${mddStr}</td>
                    <td class="col-volatility font-mono" style="color: var(--text-secondary);">${volStr}</td>
                    <td class="col-fee font-mono">${item.fee_rate}</td>
                    <td class="col-scale font-mono" style="color: var(--text-secondary);">${item.scale || '--'}</td>
                    <td class="col-status"><span class="status-badge ${statusClass}">${statusText}</span></td>
                    <td class="col-date" style="color: var(--text-secondary);">${item.inception_date || '--'}</td>
                </tr>
            `;
        }).join('');

        // 2. 移动端现代金融卡片流渲染 (方案 A: 4列数据网格 + 全宽资产配置条)
        let mobileCardsHtml = filtered.map((item, index) => {
            const rank = index + 1;
            const rankBadgeClass = rank === 1 ? 'rank-top1' : rank === 2 ? 'rank-top2' : rank === 3 ? 'rank-top3' : 'rank-other';

            const r1y = item.return_1y;
            const r1yClass = typeof APP_CONFIG !== 'undefined' ? APP_CONFIG.getChangeClass(r1y) : (r1y > 0 ? 'text-up' : r1y < 0 ? 'text-down' : '');
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
            const allocInfo = this._calcNormalizedAllocation(item);
            let allocMobileHtml = '';
            if (allocInfo && allocInfo.segments.length > 0) {
                const barHtml = allocInfo.segments.map(s => {
                    const w = s.pctStr;
                    return `<div class="${s.cls}" style="flex: 0 0 ${w}%; width: ${w}%;"></div>`;
                }).join('');

                allocMobileHtml = `
                    <div class="qdii-mcard-alloc-box" title="${allocInfo.tooltip}">
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
                    📌 <strong>【标的基准】${indexName} 原生指数近1年收益：<span class="text-up">+${utils.formatPercentage(activeBenchmark)}</span></strong>
                </div>
                <div class="qdii-legend-group">
                    <span class="qdii-legend-tag tag-us">美股</span>
                    <span class="qdii-legend-tag tag-hk">港股</span>
                    <span class="qdii-legend-tag tag-cn">A股</span>
                    <span class="qdii-legend-tag tag-other">日韩/台股</span>
                    <span class="qdii-legend-tag tag-cash">现金</span>
                    <span class="qdii-legend-tag tag-bond">债券</span>
                </div>
            </div>
        ` : (this.currentFilter === 'active' ? `
            <div style="padding: 10px 14px; margin-bottom: 12px; border-radius: 6px; background: var(--bg-body); border: 1px solid var(--border-light); font-size: clamp(0.72rem, 2.5vw, 0.78rem); color: var(--text-secondary); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                <div>
                    📌 <strong>【精选主动 & 特色 QDII】全市场共 26 只精选标的 · 全球动态跨市场配置</strong>
                </div>
                <div class="qdii-legend-group">
                    <span class="qdii-legend-tag tag-us">美股</span>
                    <span class="qdii-legend-tag tag-hk">港股</span>
                    <span class="qdii-legend-tag tag-cn">A股</span>
                    <span class="qdii-legend-tag tag-other">日韩/台股</span>
                    <span class="qdii-legend-tag tag-cash">现金</span>
                    <span class="qdii-legend-tag tag-bond">债券</span>
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
                            <th class="col-return">收益</th>
                            <th class="col-drawdown">近1年回撤</th>
                            <th class="col-volatility">年化波动率</th>
                            <th class="col-fee">综合费率</th>
                            <th class="col-scale">资产规模</th>
                            <th class="col-status">状态</th>
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

            // 客户端防御性去重，避免偶发上游脏数据造成同一标的重复渲染
            const seenKeys = new Set();
            const uniqueHoldings = [];
            (data.holdings || []).forEach(h => {
                const key = h.stock_code ? h.stock_code.trim() : (h.stock_name ? h.stock_name.trim() : '');
                if (key && !seenKeys.has(key)) {
                    seenKeys.add(key);
                    uniqueHoldings.push(h);
                }
            });
            const holdings = uniqueHoldings;
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
                
                // 渲染持仓证券类型徽章 (与主表格/卡片顶栏图例严格对齐配色规范)
                let badgeHtml = '';
                if (h.stock_type) {
                    let bgColor = 'rgba(156, 163, 175, 0.12)';
                    let textColor = '#6b7280';
                    let borderColor = 'rgba(156, 163, 175, 0.25)';
                    
                    if (h.stock_type === 'A股') {
                        bgColor = 'rgba(222, 41, 16, 0.12)';
                        textColor = '#de2910';
                        borderColor = 'rgba(222, 41, 16, 0.25)';
                    } else if (h.stock_type === '美股') {
                        bgColor = 'rgba(37, 99, 235, 0.12)';
                        textColor = '#2563eb';
                        borderColor = 'rgba(37, 99, 235, 0.25)';
                    } else if (h.stock_type === '港股') {
                        bgColor = 'rgba(147, 51, 234, 0.12)';
                        textColor = '#9333ea';
                        borderColor = 'rgba(147, 51, 234, 0.25)';
                    } else if (['日股', '台股', '韩股', '日韩/台股', '日韩台股'].includes(h.stock_type)) {
                        bgColor = 'rgba(249, 115, 22, 0.12)';
                        textColor = '#ea580c';
                        borderColor = 'rgba(249, 115, 22, 0.25)';
                    } else if (h.stock_type === '现金') {
                        bgColor = 'rgba(16, 185, 129, 0.12)';
                        textColor = '#10b981';
                        borderColor = 'rgba(16, 185, 129, 0.25)';
                    } else if (h.stock_type === '债券') {
                        bgColor = 'rgba(245, 158, 11, 0.12)';
                        textColor = '#d97706';
                        borderColor = 'rgba(245, 158, 11, 0.25)';
                    } else if (h.stock_type === '其他' || h.stock_type === '其它') {
                        bgColor = 'rgba(156, 163, 175, 0.12)';
                        textColor = '#6b7280';
                        borderColor = 'rgba(156, 163, 175, 0.25)';
                    }
                    
                    badgeHtml = `<span style="font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; font-weight: 700; background: ${bgColor}; color: ${textColor}; border: 1px solid ${borderColor}; display: inline-flex; align-items: center; justify-content: center; line-height: 1; vertical-align: middle;">${h.stock_type}</span>`;
                }

                // 计算较上季变化渲染内容
                let changeHtml = '';
                if (h.change_status === 'new') {
                    changeHtml = `<span style="font-size: 0.68rem; padding: 2px 6px; border-radius: 4px; font-weight: bold; background: rgba(59, 130, 246, 0.1); color: var(--accent-blue); border: 1px solid rgba(59, 130, 246, 0.25); display: inline-flex; align-items: center; gap: 2px;"><i data-lucide="sparkles" style="width: 10px; height: 10px;"></i>新进</span>`;
                } else if (h.change_status === 'up') {
                    changeHtml = `<span style="color: var(--color-up, #ef4444); font-weight: 700; font-family: monospace; font-size: 0.8rem; display: inline-flex; align-items: center; gap: 2px;">▲ ${h.change_pct}</span>`;
                } else if (h.change_status === 'down') {
                    changeHtml = `<span style="color: var(--color-down, #22c55e); font-weight: 700; font-family: monospace; font-size: 0.8rem; display: inline-flex; align-items: center; gap: 2px;">▼ ${h.change_pct}</span>`;
                } else {
                    changeHtml = `<span style="color: var(--text-tertiary); font-family: monospace; font-size: 0.8rem;">0.00%</span>`;
                }

                return `
                    <tr>
                        <td style="width: 24px; text-align: center; font-weight: bold; color: var(--text-secondary); font-size: 0.78rem;">${h.rank}</td>
                        <td style="font-weight: 600;">
                            <div style="font-size: 0.84rem; line-height: 1.25;">${h.stock_name}</div>
                            <div style="font-size: 0.72rem; color: var(--text-tertiary); font-family: monospace; margin-top: 2px; display: flex; align-items: center; gap: 4px;">
                                <span>${h.stock_code}</span>
                                ${badgeHtml}
                            </div>
                        </td>
                        <td style="width: 70px; text-align: right; font-weight: 700; font-family: monospace; white-space: nowrap; font-size: 0.86rem;">
                            ${h.ratio_pct}
                        </td>
                        <td style="width: 75px; text-align: right; font-weight: 600; white-space: nowrap;">
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
                    <span>📈 近1年收益：<strong class="${fundItem.return_1y != null ? (typeof APP_CONFIG !== 'undefined' ? APP_CONFIG.getChangeClass(fundItem.return_1y) : (fundItem.return_1y > 0 ? 'text-up' : 'text-down')) : ''}">${r1y}</strong></span>
                    <span>📉 近1年回撤：<strong>${mdd}</strong></span>
                    <span>⚡ 年化波动率：<strong>${vol}</strong></span>
                    <span>📐 夏普比率：<strong>${sharpe}</strong></span>
                </div>
                <table class="qdii-holding-table">
                    <thead>
                        <tr>
                            <th style="width: 24px; text-align: center;">#</th>
                            <th>股票名称 / 代码</th>
                            <th style="width: 70px; text-align: right; white-space: nowrap;">持仓占比</th>
                            <th style="width: 75px; text-align: right; white-space: nowrap;">较上季</th>
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

