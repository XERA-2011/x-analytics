/**
 * 基金模块控制器
 */
class FundsController {
    constructor() {
        this.currentType = '全部';
        this.isLoading = false;
        this.debounceTimer = null;
        this.retryTimer = null;
        this.retryCount = 0;
        this.maxRetries = 3;
        this.initFilterButtons();
    }

    initFilterButtons() {
        // 延迟绑定，等待 DOM 加载
        setTimeout(() => {
            const buttons = document.querySelectorAll('.fund-type-btn');
            buttons.forEach(btn => {
                btn.addEventListener('click', () => {
                    // 防止重复点击
                    if (this.isLoading) return;

                    // 相同类型不重复加载
                    if (this.currentType === btn.dataset.type) return;

                    // 更新按钮状态
                    buttons.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');

                    // 更新当前类型
                    this.currentType = btn.dataset.type;

                    // 重置重试计数
                    this.retryCount = 0;
                    this.clearRetryTimer();

                    // 防抖：300ms 内的连续点击只执行最后一次
                    if (this.debounceTimer) {
                        clearTimeout(this.debounceTimer);
                    }
                    this.debounceTimer = setTimeout(() => {
                        this.loadFundRanking();
                    }, 300);
                });
            });
        }, 100);
    }

    clearRetryTimer() {
        if (this.retryTimer) {
            clearTimeout(this.retryTimer);
            this.retryTimer = null;
        }
    }

    async loadData() {
        console.log('📊 加载基金数据...');
        this.retryCount = 0;
        await this.loadFundRanking();
    }

    async loadFundRanking() {
        const container = document.getElementById('fund-ranking');
        if (!container) return;

        // 防止并发加载
        if (this.isLoading) return;
        this.isLoading = true;

        // 显示加载状态
        container.innerHTML = '<div class="loading">Loading...</div>';

        try {
            const data = await api.getFundRanking(this.currentType, 10);

            // 处理 warming_up 状态：自动重试
            if (data._warming_up && this.retryCount < this.maxRetries) {
                this.retryCount++;
                console.log(`📊 基金数据预热中，3秒后重试 (${this.retryCount}/${this.maxRetries})...`);
                // 显示带重试信息的加载状态
                container.innerHTML = `<div class="loading warming-up"><i data-lucide="clock" width="16"></i> 数据预热中，3秒后自动刷新 (${this.retryCount}/${this.maxRetries})</div>`;
                if (window.lucide) lucide.createIcons();
                this.isLoading = false;
                this.retryTimer = setTimeout(() => this.loadFundRanking(), 3000);
                return;
            }

            this.renderFundRanking(data);
        } catch (error) {
            console.error('加载基金排行失败:', error);
            utils.renderError('fund-ranking', '基金数据加载失败');
        } finally {
            this.isLoading = false;
        }
    }

    renderFundRanking(data) {
        const container = document.getElementById('fund-ranking');
        if (!container) return;

        // 错误处理
        if (data._error) {
            utils.renderError('fund-ranking', data.message || '暂无数据');
            return;
        }

        // 预热处理
        if (data._warming_up) {
            utils.renderWarmingUp('fund-ranking');
            return;
        }

        // 数据结构检查 & 兼容性处理
        // 新接口返回 { gainers: [], losers: [], ... }
        // 旧逻辑暂时兼容一下（虽然很快会被刷新覆盖）
        let gainers = [];
        let losers = [];
        let total = 0;
        let dateStr = '';

        if (data.gainers && data.losers) {
            gainers = data.gainers;
            losers = data.losers;
            total = data.total;
            dateStr = data.update_time?.split(' ')[0] || ''; //这里可能需要取 item 里的 date
            if (gainers.length > 0) dateStr = gainers[0].date;
        } else if (data.items) {
            // 旧数据回退：只显示 items 为涨幅榜，跌幅榜为空
            gainers = data.items;
            total = data.total || 0;
            if (gainers.length > 0) dateStr = gainers[0].date;
        } else {
            utils.renderError('fund-ranking', '数据格式升级中，请刷新...');
            return;
        }

        // 渲染 HTML：左右两列布局
        const renderTable = (list, title, isGainer) => {
            if (!list || list.length === 0) return `<div class="empty-state">暂无${title}数据</div>`;

            const rows = list.map((fund, index) => {
                const dailyChange = fund.daily_change;
                // 涨幅榜全红，跌幅榜全绿（CN习惯）
                // 或者根据实际数值染色
                const cls = dailyChange > 0 ? 'text-up' : dailyChange < 0 ? 'text-down' : '';
                const sign = dailyChange > 0 ? '+' : '';

                return `
                    <div class="fund-row">
                        <div class="col-rank">${index + 1}</div>
                        <div class="col-name" title="${fund.name}">
                            <span class="name">${fund.name}</span>
                            <span class="code">${fund.code}</span>
                        </div>
                        <div class="col-change ${cls}">${sign}${dailyChange != null ? dailyChange.toFixed(2) : '--'}%</div>
                    </div>
                `;
            }).join('');

            return `
                <div class="fund-list-column">
                    <div class="column-header">${title} (Top 10)</div>
                    <div class="fund-table-header">
                        <div class="col-rank">排名</div>
                        <div class="col-name">基金名称</div>
                        <div class="col-change">日涨跌</div>
                    </div>
                    <div class="fund-table-body">
                        ${rows}
                    </div>
                </div>
            `;
        };

        const html = `
            <div class="funds-dual-container">
                ${renderTable(gainers, '涨幅榜', true)}
                ${renderTable(losers, '跌幅榜', false)}
            </div>
        `;

        container.innerHTML = html;

        // 更新标题
        const header = document.querySelector('#funds .card-header .card-title');
        if (header) {
            let title = '基金涨跌幅排行';
            if (data.fund_type) title += ` (${data.fund_type})`;
            // if (total) title += ` · 共${total}只`; // 分榜后这个总数可能不是重点了
            if (dateStr) title += ` · ${dateStr}净值`;
            header.textContent = title;
        }
    }
}
