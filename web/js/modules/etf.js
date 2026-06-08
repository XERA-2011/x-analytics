// ETF 市场模块
// 依赖: api.js, charts.js, utils.js

class ETFController {
    async loadData() {
        const promises = [
            this.loadETFHeatmap(),
        ];
        await Promise.allSettled(promises);
    }

    async loadETFHeatmap() {
        try {
            const data = await api.getETFHeatmap();
            this.renderETFHeatmap(data);
            this.renderETFRanking(data);
        } catch (error) {
            console.error('加载 ETF 热力图失败:', error);
            utils.renderError('etf-heatmap', 'ETF 热力图加载失败');
            utils.renderError('etf-ranking', 'ETF 排行榜加载失败');
        }
    }

    renderETFHeatmap(data) {
        const container = document.getElementById('etf-heatmap');
        if (!container) return;

        if (data.error || !data.categories || data.categories.length === 0) {
            utils.renderError('etf-heatmap', data.error || 'ETF 数据为空');
            return;
        }

        // 转换为 flat treemap 数据格式
        // 展开所有类别的 ETF，作为单独的区块渲染
        const treemapData = [];
        data.categories.forEach(cat => {
            if (cat.children && Array.isArray(cat.children)) {
                cat.children.forEach(etf => {
                    treemapData.push({
                        name: etf.name,
                        code: etf.code,
                        value: etf.value || 0,
                        change_pct: etf.change_pct,
                        turnover: etf.turnover,
                        amount: etf.amount
                    });
                });
            }
        });

        // 设置合适的高度
        container.style.height = '800px';
        window.charts.renderTreemap('etf-heatmap', treemapData);

        // 更新匹配信息
        const matchInfo = document.getElementById('etf-match-info');
        if (matchInfo) {
            matchInfo.textContent = `已匹配 ${data.matched}/${data.total} 只 ETF`;
        }
    }

    renderETFRanking(data) {
        const container = document.getElementById('etf-ranking');
        if (!container) return;

        if (data.error || (!data.top_gainers?.length && !data.top_losers?.length)) {
            utils.renderError('etf-ranking', data.error || '排行榜数据为空');
            return;
        }

        const renderList = (items, isGainer) => {
            if (!items || items.length === 0) {
                return '<div class="empty-state">暂无数据</div>';
            }

            return items.map((etf, i) => {
                const changePct = etf.change_pct != null ? etf.change_pct : 0;
                const colorClass = changePct > 0 ? 'text-up' : changePct < 0 ? 'text-down' : '';
                const sign = changePct > 0 ? '+' : '';
                const amount = etf.amount != null ? (etf.amount / 100000000).toFixed(1) + '亿' : '--';

                return `
                    <div class="list-item">
                        <div class="item-main">
                            <div class="item-title">${i + 1}. ${etf.name}</div>
                            <div class="item-subtitle">${etf.code} · 成交 ${amount}</div>
                        </div>
                        <div class="item-value ${colorClass}" style="font-family: var(--font-mono);">
                            ${sign}${changePct.toFixed(2)}%
                        </div>
                    </div>
                `;
            }).join('');
        };

        const html = `
            <div class="sector-ranking" style="border-bottom: none; margin-bottom: 0; padding-bottom: 0;">
                <div class="ranking-column">
                    <div class="ranking-header up" style="font-size: 12px;">📈 涨幅榜</div>
                    ${renderList(data.top_gainers, true)}
                </div>
                <div class="ranking-column">
                    <div class="ranking-header down" style="font-size: 12px;">📉 跌幅榜</div>
                    ${renderList(data.top_losers, false)}
                </div>
            </div>
        `;

        container.innerHTML = html;
    }
}
