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
        console.log('📊 加载中国市场数据...');

        // Setup sort buttons immediately (only once)
        if (!this._sortButtonsBound) {
            this.setupSortButtons();
            this._sortButtonsBound = true;
        }

        const promises = [
            this.loadCNFearGreed(),
            this.loadCNIndices(),
            this.loadCNLeaders(),


            this.loadCNBonds(),
            this.loadLPR()
        ];
        await Promise.allSettled(promises);
    }

    async loadCNIndices() {
        try {
            const data = await api.getCNIndices();
            this.renderCNIndices(data);
        } catch (error) {
            console.error('加载大盘指数失败:', error);
            utils.renderError('cn-indices', '大盘指数加载失败');
        }
    }

    renderCNIndices(data) {
        const container = document.getElementById('cn-indices');
        if (!container) return;

        if (data.error || !data.indices) {
            utils.renderError('cn-indices', data.error || '暂无数据');
            return;
        }

        const indices = data.indices || [];
        const html = indices.map(item => {
            const changeVal = item.change_pct;
            const changeClass = changeVal > 0 ? 'text-up' : changeVal < 0 ? 'text-down' : '';
            const sign = changeVal > 0 ? '+' : '';

            return `
                <div class="index-item">
                    <div class="index-name">${item.name}</div>
                    <div class="index-price ${changeClass}">${utils.formatNumber(item.price)}</div>
                    <div class="index-change ${changeClass}">
                        ${sign}${utils.formatNumber(item.change_amount)} 
                        (${sign}${utils.formatPercentage(changeVal)})
                    </div>
                    <div class="index-vol">成交 ${utils.formatNumber(item.amount / 100000000)}亿</div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
        container.classList.remove('loading');
    }

    async loadLPR() {
        try {
            const data = await api.getLPR();
            this.renderLPR(data);
        } catch (error) {
            console.error('加载 LPR 失败:', error);
            utils.renderError('macro-lpr', 'LPR 数据加载失败');
        }
    }

    renderLPR(data) {
        const container = document.getElementById('macro-lpr');
        if (!container) return;

        if (data.error || !data.current) {
            utils.renderError('macro-lpr', data.error || '暂无数据');
            return;
        }

        // Bind info button
        const infoBtn = document.getElementById('info-lpr');
        if (infoBtn) {
            infoBtn.onclick = () => utils.showInfoModal('LPR 利率', data.description || 'LPR 贷款市场报价利率，每月 20 日公布');
        }

        const { current } = data;
        const change1y = current.lpr_1y_change;
        const change5y = current.lpr_5y_change;

        const html = `
            <div class="heat-grid" style="grid-template-columns: 1fr 1fr;">
                <div class="heat-cell">
                    <div class="item-sub">1年期 LPR</div>
                    <div class="fg-score" style="font-size: 28px;">${current.lpr_1y}%</div>
                    ${change1y !== 0 ? `<div class="item-sub ${change1y < 0 ? 'text-down' : 'text-up'}">${change1y > 0 ? '+' : ''}${change1y}bp</div>` : '<div class="item-sub">持平</div>'}
                </div>
                <div class="heat-cell">
                    <div class="item-sub">5年期 LPR</div>
                    <div class="fg-score" style="font-size: 28px;">${current.lpr_5y}%</div>
                    ${change5y !== 0 ? `<div class="item-sub ${change5y < 0 ? 'text-down' : 'text-up'}">${change5y > 0 ? '+' : ''}${change5y}bp</div>` : '<div class="item-sub">持平</div>'}
                </div>
            </div>
            <div style="text-align: center; font-size: 11px; color: var(--text-tertiary); margin-top: 8px;">
                最新报价日期: ${current.date}
            </div>
        `;
        container.innerHTML = html;
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
                api.getCNTopGainers().catch(e => ({ error: '数据加载失败' })),
                api.getCNTopLosers().catch(e => ({ error: '数据加载失败' }))
            ]);

            // Store data for re-sorting (check for error before accessing sectors)
            this.gainersData = gainers.sectors || [];
            this.losersData = losers.sectors || [];

            // Store explanation for info button (分别存储领涨和领跌的说明)
            this.gainersExplanation = gainers.explanation || '';
            this.losersExplanation = losers.explanation || '';

            this.renderCNLeaders(gainers, losers);

            // Bind info button events (使用各自的说明)
            const infoBtn = document.getElementById('info-cn-sectors');
            const infoBtnLosers = document.getElementById('info-cn-sectors-losers');

            if (this.gainersExplanation && infoBtn) {
                infoBtn.onclick = () => {
                    utils.showInfoModal('板块分析说明', this.gainersExplanation);
                };
                infoBtn.style.display = 'flex';
            }
            if (this.losersExplanation && infoBtnLosers) {
                infoBtnLosers.onclick = () => {
                    utils.showInfoModal('板块分析说明', this.losersExplanation);
                };
                infoBtnLosers.style.display = 'flex';
            }
        } catch (error) {
            console.error('加载领涨领跌板块失败:', error);
            utils.renderError('cn-gainers', '系统错误');
            utils.renderError('cn-losers', '系统错误');
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
            infoBtn.style.display = 'flex';
        }

        // Center content
        container.style.justifyContent = 'center';

        container.innerHTML = `
            <div class="fg-gauge" id="cn-fear-greed-gauge"></div>
            <div class="fg-info" style="flex: 0 1 auto;">

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
        if (gainers.error) {
            utils.renderError('cn-gainers', gainers.error);
        } else {
            this.renderSectorList('cn-gainers', gainers.sectors || [], '领涨', this.currentSort.gainers);
        }

        if (losers.error) {
            utils.renderError('cn-losers', losers.error);
        } else {
            this.renderSectorList('cn-losers', losers.sectors || [], '领跌', this.currentSort.losers);
        }
    }

    renderSectorList(containerId, sectors, label = '领涨', sortBy = 'pct') {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!sectors || sectors.length === 0) {
            utils.renderError(containerId, '暂无数据');
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
            const analysis = sector.analysis || {};
            const heat = analysis.heat || {};
            const tip = analysis.tip || '';
            // 使用 analysis.turnover 或回退到 sector.turnover
            const turnover = analysis.turnover ?? sector.turnover ?? 0;

            // 生成分析标签 HTML (显示标签 + 换手率)
            const analysisHtml = tip ? `
                <div class="sector-analysis">
                    <span class="heat-tag heat-${heat.color || 'gray'}">${heat.level || ''} ${turnover}%</span>
                    <span class="analysis-tip">${tip}</span>
                </div>
            ` : '';

            return `
                <div class="list-item sector-item">
                    <div class="item-main">
                        <span class="item-title">${sector.name}</span>
                        <span class="item-sub">${sector.stock_count}家 | ${label}: ${sector.leading_stock || '--'}</span>
                        ${analysisHtml}
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





    renderCNBonds(data) {
        const container = document.getElementById('cn-bonds');
        if (!container) return;

        if (!data || data.error) {
            utils.renderError('cn-bonds', data && data.error ? data.error : '暂无数据');
            return;
        }

        if (data.status === 'warming_up') {
            utils.renderWarmingUp('cn-bonds');
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

    // =========================================================================
    // 宏观数据模块
    // =========================================================================


}
