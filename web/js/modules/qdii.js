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
            this.renderStats();
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

    renderStats() {
        const statsContainer = document.getElementById('qdii-stats');
        if (!statsContainer || !this.rawFunds.length) return;

        const nasdaqFunds = this.rawFunds.filter(f => f.index_code === 'NDX');
        const sp500Funds = this.rawFunds.filter(f => f.index_code === 'SPX');

        const calcAvgReturn = (arr) => {
            const valid = arr.filter(f => f.return_1y != null);
            if (!valid.length) return 0;
            return valid.reduce((sum, f) => sum + f.return_1y, 0) / valid.length;
        };

        const ndxBenchmark = this.benchmarks.NDX?.return_1y || 21.14;
        const spxBenchmark = this.benchmarks.SPX?.return_1y || 16.48;

        const nasdaqAvgVal = calcAvgReturn(nasdaqFunds);
        const sp500AvgVal = calcAvgReturn(sp500Funds);

        const nasdaqAvg = utils.formatPercentage(nasdaqAvgVal);
        const sp500Avg = utils.formatPercentage(sp500AvgVal);

        const ndxDiff = utils.formatPercentage(nasdaqAvgVal - ndxBenchmark);
        const spxDiff = utils.formatPercentage(sp500AvgVal - spxBenchmark);

        statsContainer.innerHTML = `
            <div class="card" style="flex: 1; padding: 14px; border-left: 3px solid #3b82f6;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="item-sub" style="color: var(--text-primary); font-weight: 600;">纳斯达克100 原生指数近1年</div>
                        <div class="fg-score text-up-us" style="font-size: 24px; margin-top: 4px;">+${utils.formatPercentage(ndxBenchmark)}</div>
                    </div>
                    <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(59, 130, 246, 0.12); color: #3b82f6; font-weight: 600;">标的基准</span>
                </div>
                <div class="item-sub" style="margin-top: 8px; font-size: 12px; color: var(--text-secondary);">
                    QDII 基金平均收益: <strong class="text-up-us">+${nasdaqAvg}</strong> (平均跟踪差额: <span style="color: var(--text-tertiary);">${ndxDiff}</span>)
                </div>
            </div>

            <div class="card" style="flex: 1; padding: 14px; border-left: 3px solid #a855f7;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="item-sub" style="color: var(--text-primary); font-weight: 600;">标普500 原生指数近1年</div>
                        <div class="fg-score text-up-us" style="font-size: 24px; margin-top: 4px;">+${utils.formatPercentage(spxBenchmark)}</div>
                    </div>
                    <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(168, 85, 247, 0.12); color: #a855f7; font-weight: 600;">标的基准</span>
                </div>
                <div class="item-sub" style="margin-top: 8px; font-size: 12px; color: var(--text-secondary);">
                    QDII 基金平均收益: <strong class="text-up-us">+${sp500Avg}</strong> (平均跟踪差额: <span style="color: var(--text-tertiary);">${spxDiff}</span>)
                </div>
            </div>

            <div class="card" style="flex: 0.8; padding: 14px;">
                <div class="item-sub">最低费率区间</div>
                <div class="fg-score" style="font-size: 24px; margin-top: 4px; color: var(--primary);">0.60%/年</div>
                <div class="item-sub" style="margin-top: 8px; font-size: 12px; color: var(--text-secondary);">含管理费 0.50% + 托管费 0.10%</div>
            </div>
        `;
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
        }

        if (!filtered.length) {
            utils.renderError('qdii-table-container', '该分类下暂无基金数据');
            return;
        }

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

            return `
                <tr>
                    <td style="text-align: center;"><span class="rank-badge ${rankBadgeClass}">${rank}</span></td>
                    <td class="font-mono" style="font-weight: 600;">${item.code}</td>
                    <td style="font-weight: 600; color: var(--primary);">${item.name}</td>
                    <td style="text-align: right;" class="font-mono">${item.fee_rate}</td>
                    <td style="text-align: right; font-weight: 700;" class="font-mono ${r1yClass}">${r1yStr}</td>
                    <td style="text-align: right; color: var(--text-tertiary);" class="font-mono">${benchmarkGapStr}</td>
                    <td style="text-align: right;" class="font-mono">${item.tracking_error || '--'}</td>
                    <td style="text-align: center; color: var(--text-secondary); font-size: 12px;">${item.inception_date || '--'}</td>
                </tr>
            `;
        }).join('');

        const benchmarkNotice = activeBenchmark != null ? `
            <div style="padding: 10px 14px; margin-bottom: 12px; border-radius: 6px; background: var(--bg-body); border: 1px solid var(--border-light); font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                <div>
                    📌 <strong>【标的基准】${indexName} 原生指数近1年收益：<span class="text-up-us">+${utils.formatPercentage(activeBenchmark)}</span></strong>
                </div>
                <div style="color: var(--text-tertiary); font-size: 11px;">
                    对比差额为 QDII 基金收益与原生指数收益的实际差距（含费率、外汇及仓位跟踪损耗）
                </div>
            </div>
        ` : '';

        container.innerHTML = `
            ${benchmarkNotice}
            <div class="table-wrapper">
                <table class="qdii-table">
                    <thead>
                        <tr>
                            <th style="width: 50px; text-align: center;">排名</th>
                            <th style="width: 80px;">代码</th>
                            <th>基金名称</th>
                            <th style="width: 90px; text-align: right;">综合费率</th>
                            <th style="width: 110px; text-align: right;">近1年收益</th>
                            <th style="width: 110px; text-align: right;">对标指数差距</th>
                            <th style="width: 100px; text-align: right;">跟踪偏离度</th>
                            <th style="width: 110px; text-align: center;">成立时间</th>
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
