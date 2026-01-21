class CNMarketController {
    async loadData() {
        console.log('📊 加载沪港深市场数据...');
        const promises = [
            this.loadCNFearGreed(),
            this.loadCNLeaders(),
            this.loadCNMarketHeat(),
            this.loadCNDividend(),
            this.loadCNBonds()
        ];
        await Promise.allSettled(promises);
    }

    async loadCNFearGreed() {
        try {
            const data = await api.getCNFearGreed();
            this.renderCNFearGreed(data);
        } catch (error) {
            console.error('加载恐慌贪婪指数失败:', error);
            utils.renderError('cn-fear-greed', '恐慌贪婪指数加载失败');
        }
    }

    async loadCNLeaders() {
        try {
            const [gainers, losers] = await Promise.all([
                api.getCNTopGainers(),
                api.getCNTopLosers()
            ]);
            this.renderCNLeaders(gainers, losers);
        } catch (error) {
            console.error('加载领涨领跌板块失败:', error);
            utils.renderError('cn-gainers', '领涨领跌板块加载失败');
        }
    }

    async loadCNMarketHeat() {
        try {
            const data = await api.getCNMarketHeat();
            this.renderCNMarketHeat(data);
        } catch (error) {
            console.error('加载市场热度失败:', error);
            utils.renderError('market-cn-heat', '市场热度加载失败');
        }
    }

    async loadCNDividend() {
        try {
            const data = await api.getCNDividendStocks();
            this.renderCNDividend(data);
        } catch (error) {
            console.error('加载红利低波数据失败:', error);
            utils.renderError('cn-dividend', '红利低波数据加载失败');
        }
    }

    async loadCNBonds() {
        try {
            const data = await api.getCNTreasuryYields();
            this.renderCNBonds(data);
        } catch (error) {
            console.error('加载国债数据失败:', error);
            utils.renderError('cn-bonds', '国债数据加载失败');
        }
    }

    renderCNFearGreed(data) {
        const container = document.getElementById('cn-fear-greed');
        if (!container) return;

        if (data.error) {
            utils.renderError('cn-fear-greed', data.error);
            return;
        }

        container.innerHTML = `
            <div class="fg-gauge" id="cn-fear-greed-gauge"></div>
            <div class="fg-info">
                <div class="fg-score class-${utils.getScoreClass(data.score)}">${data.score}</div>
                <div class="fg-level">${data.level}</div>
                <div class="fg-desc">${data.description}</div>
            </div>
        `;

        if (window.charts) {
            setTimeout(() => {
                charts.createFearGreedGauge('cn-fear-greed-gauge', data);
            }, 100);
        }
    }

    renderCNLeaders(gainers, losers) {
        this.renderSectorList('cn-gainers', gainers.sectors || []);
        this.renderSectorList('cn-losers', losers.sectors || []);
    }

    renderSectorList(containerId, sectors) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!sectors || sectors.length === 0) {
            container.innerHTML = '<div class="loading">暂无数据</div>';
            return;
        }

        const html = sectors.map(sector => {
            const change = utils.formatChange(sector.change_pct);
            return `
                <div class="list-item">
                    <div class="item-main">
                        <span class="item-title">${sector.name}</span>
                        <span class="item-sub">${sector.stock_count}家 | 领涨: ${sector.leading_stock || '--'}</span>
                    </div>
                    <div style="text-align: right;">
                        <div class="item-value">${utils.formatNumber(sector.total_market_cap / 100000000)}亿</div>
                        <div class="item-change ${change.class}">${change.text}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    renderCNMarketHeat(data) {
        const container = document.getElementById('market-cn-heat');
        if (!container) return;

        if (data.error) {
            utils.renderError('market-cn-heat', data.error);
            return;
        }

        const html = `
            <div class="heat-cell">
                <div class="fg-score">${data.heat_score}</div>
                <div class="fg-level">${data.heat_level}</div>
            </div>
            <div class="heat-cell">
                <div class="item-sub">成交额</div>
                <div class="heat-val">${utils.formatNumber(data.total_turnover)}亿</div>
            </div>
            <div class="heat-cell">
                <div class="item-sub">涨跌比</div>
                <div class="heat-val">${data.rise_fall_ratio}</div>
            </div>
            <div class="heat-cell">
                <div class="item-sub">强势股</div>
                <div class="heat-val">${data.strong_stocks}</div>
            </div>
        `;

        container.innerHTML = html;
    }

    renderCNDividend(data) {
        const container = document.getElementById('cn-dividend');
        if (!container) return;

        if (data.error || !data.stocks) {
            utils.renderError('cn-dividend', data.error || '暂无数据');
            return;
        }

        const stats = data.strategy_stats || {};

        const statsHtml = `
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; padding-bottom: 12px; margin-bottom: 12px; border-bottom: 1px solid var(--border-light); text-align: center;">
                <div>
                    <div class="item-sub">均股息</div>
                    <div class="heat-val">${utils.formatPercentage(stats.avg_dividend_yield)}</div>
                </div>
                <div>
                    <div class="item-sub">均PE</div>
                    <div class="heat-val">${utils.formatNumber(stats.avg_pe_ratio)}</div>
                </div>
                <div>
                    <div class="item-sub">低波股</div>
                    <div class="heat-val">${stats.low_volatility_count || 0}</div>
                </div>
            </div>
        `;

        const listHtml = data.stocks.slice(0, 10).map(stock => `
            <div class="list-item">
                <div class="item-main">
                    <span class="item-title">${stock.name}</span>
                    <span class="item-sub">${stock.code}</span>
                </div>
                <div>
                    <div class="item-value" style="color: var(--accent-red)">${utils.formatPercentage(stock.estimated_dividend_yield)}</div>
                    <div class="item-change">PE ${utils.formatNumber(stock.pe_ratio)}</div>
                </div>
            </div>
        `).join('');

        container.innerHTML = statsHtml + listHtml;
    }

    renderCNBonds(data) {
        const container = document.getElementById('cn-bonds');
        if (!container) return;

        if (!data || data.error) {
            utils.renderError('cn-bonds', data && data.error ? data.error : '暂无数据');
            return;
        }

        const yieldCurve = data.yield_curve || {};
        const keyRates = data.key_rates;

        let curveItems = [];
        if (Array.isArray(yieldCurve)) {
            curveItems = yieldCurve;
        } else {
            curveItems = Object.entries(yieldCurve).map(([period, rate]) => ({
                period: period.toUpperCase(),
                yield: rate,
                change_bp: data.yield_changes ? (data.yield_changes[period] || 0) : 0
            }));
        }

        if (keyRates) {
            const html = `
                <div class="bond-scroll">
                    ${curveItems.map(item => `
                        <div class="bond-item">
                            <span class="bond-name">${item.period}</span>
                            <span class="bond-rate">${utils.formatPercentage(item.yield)}</span>
                             <span class="bond-change ${utils.formatChange(item.change_bp).class}" style="font-size: 10px; display: block;">
                                ${item.change_bp > 0 ? '+' : ''}${item.change_bp}bp
                            </span>
                        </div>
                    `).join('')}
                </div>
                <div style="font-size: 12px; padding: 8px; color: var(--text-secondary); border-top: 1px solid var(--border-light); text-align: center;">
                    <div>10年期-2年期 = 期限利差: <span style="font-weight: 600;">${utils.formatNumber(keyRates.spread_10y_2y, 3)}%</span></div>
                    <div style="margin-top: 4px; color: ${keyRates.spread_10y_2y < 0 ? 'var(--accent-red)' : 'var(--text-primary)'}">
                        ${data.curve_analysis?.comment || ''}
                    </div>
                </div>
            `;
            container.innerHTML = html;
        } else {
            const html = curveItems.map(item => `
                <div class="bond-item">
                    <span class="bond-name">${item.period || item.name}</span>
                    <span class="bond-rate">${item.yield || item.value}%</span>
                </div>
            `).join('');
            container.innerHTML = html;
        }

    }
}
