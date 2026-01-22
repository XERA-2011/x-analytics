class CNMarketController {
    constructor() {
        // Store fetched data for re-sorting
        this.gainersData = [];
        this.losersData = [];
        this.currentSort = {
            gainers: 'pct',
            losers: 'pct'
        };
        this._sortButtonsBound = false;
    }

    async loadData() {
        console.log('📊 加载沪港深市场数据...');

        // Setup sort buttons immediately (only once)
        if (!this._sortButtonsBound) {
            this.setupSortButtons();
            this._sortButtonsBound = true;
        }

        const promises = [
            this.loadCNFearGreed(),
            this.loadCNLeaders(),
            this.loadCNMarketHeat(),
            this.loadCNDividend(),
            this.loadCNBonds()
        ];
        await Promise.allSettled(promises);
    }

    setupSortButtons() {
        const sortBtns = document.querySelectorAll('.sort-btn[data-target="gainers"], .sort-btn[data-target="losers"]');
        sortBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = btn.dataset.target; // 'gainers' or 'losers'
                const sortBy = btn.dataset.sort;   // 'pct' or 'cap'

                // Update active state for sibling buttons
                const siblings = document.querySelectorAll(`.sort-btn[data-target="${target}"]`);
                siblings.forEach(s => s.classList.remove('active'));
                btn.classList.add('active');

                // Update current sort and re-render
                this.currentSort[target] = sortBy;
                if (target === 'gainers') {
                    this.renderSectorList('cn-gainers', this.gainersData, '领涨', sortBy);
                } else {
                    this.renderSectorList('cn-losers', this.losersData, '领跌', sortBy);
                }
            });
        });
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
            // Store data for re-sorting
            this.gainersData = gainers.sectors || [];
            this.losersData = losers.sectors || [];
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

        // Bind Info Button
        const infoBtn = document.getElementById('info-cn-fear');
        if (infoBtn && data.explanation) {
            infoBtn.onclick = () => utils.showInfoModal('恐慌贪婪指数 (CN)', data.explanation);
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
        this.renderSectorList('cn-gainers', gainers.sectors || [], '领涨', this.currentSort.gainers);
        this.renderSectorList('cn-losers', losers.sectors || [], '领跌', this.currentSort.losers);
    }

    renderSectorList(containerId, sectors, label = '领涨', sortBy = 'pct') {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!sectors || sectors.length === 0) {
            container.innerHTML = '<div class="loading">暂无数据</div>';
            return;
        }

        // Sort sectors based on sortBy parameter
        const sortedSectors = [...sectors].sort((a, b) => {
            if (sortBy === 'cap') {
                // Sort by market cap (descending)
                return (b.total_market_cap || 0) - (a.total_market_cap || 0);
            } else {
                // Sort by change_pct (descending for gainers, ascending for losers)
                if (label === '领跌') {
                    return (a.change_pct || 0) - (b.change_pct || 0);
                }
                return (b.change_pct || 0) - (a.change_pct || 0);
            }
        });

        const html = sortedSectors.map(sector => {
            const change = utils.formatChange(sector.change_pct);
            return `
                <div class="list-item">
                    <div class="item-main">
                        <span class="item-title">${sector.name}</span>
                        <span class="item-sub">${sector.stock_count}家 | ${label}: ${sector.leading_stock || '--'}</span>
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

        // Bind Info Button
        const infoBtn = document.getElementById('info-cn-heat');
        if (infoBtn && data.explanation) {
            infoBtn.onclick = () => utils.showInfoModal('市场热度指数', data.explanation);
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

        // Bind Info Button - Priority Binding
        const infoBtn = document.getElementById('info-cn-dividend');
        if (infoBtn) {
            infoBtn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                // Fallback description if missing
                const desc = data.description || '暂无说明 (Description missing in data)';
                utils.showInfoModal('红利低波动策略', desc);
            };
        } else {
            console.error('CRITICAL: info-cn-dividend button NOT FOUND');
        }

        if (data.error || !data.stocks) {
            utils.renderError('cn-dividend', data.error || '暂无数据');
            return;
        }

        const stats = data.strategy_stats || {};

        const signal = stats.signal || { text: '暂无信号', color: '#909399' };
        const bankWeight = stats.bank_weight || 0;

        // 统计区：信号、银行占比 + 核心指标
        const statsHtml = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding: 0 4px;">
                <div style="font-size: 12px; font-weight: 600; color: ${signal.color}; border: 1px solid ${signal.color}; padding: 2px 8px; border-radius: 4px;">
                    ${signal.text}
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; gap: 4px;">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background-color: ${bankWeight > 40 ? '#F56C6C' : '#E6A23C'};"></span>
                    银行仓位 ${bankWeight}%
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; padding-bottom: 12px; margin-bottom: 12px; border-bottom: 1px solid var(--border-light); text-align: center;">
                <div>
                    <div class="item-sub">加权ROE</div>
                    <div class="heat-val" style="color: var(--accent-red)">${utils.formatPercentage(stats.avg_roe)}</div>
                </div>
                <div>
                    <div class="item-sub">盈利收益</div>
                    <div class="heat-val" style="color: var(--accent-red)">${utils.formatPercentage(stats.avg_earnings_yield)}</div>
                </div>
                <div>
                    <div class="item-sub">加权PE</div>
                    <div class="heat-val">${utils.formatNumber(stats.avg_pe_ratio)}</div>
                </div>
                <div>
                    <div class="item-sub">涨/跌</div>
                    <div class="heat-val">${stats.up_count || 0}/${stats.down_count || 0}</div>
                </div>
            </div>
        `;

        // 成分股列表：显示权重和实时涨跌，增加第二行价值指标
        const listHtml = data.stocks.slice(0, 10).map(stock => {
            const change = utils.formatChange(stock.change_pct);
            return `
                <div class="list-item" style="flex-wrap: wrap;">
                    <div class="item-main">
                        <span class="item-title">${stock.name}</span>
                        <span class="item-sub">${stock.code}</span>
                    </div>
                    <div style="text-align: right;">
                        <div class="item-value">${utils.formatNumber(stock.price)}</div>
                        <div class="item-change ${change.class}">${change.text}</div>
                    </div>
                    <!-- 第二行：深度价值指标 -->
                    <div style="width: 100%; display: flex; justify-content: space-between; margin-top: 4px; padding-top: 4px; border-top: 1px dashed var(--border-light); font-size: 11px; color: var(--text-tertiary);">
                        <span>权重 ${utils.formatNumber(stock.weight)}%</span>
                        <span>ROE: ${utils.formatNumber(stock.roe)}%</span>
                        <span>E/P: ${utils.formatNumber(stock.earnings_yield)}%</span>
                        <span>PB: ${utils.formatNumber(stock.pb_ratio)}</span>
                    </div>
                </div>
            `;
        }).join('');

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
