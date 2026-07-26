// 全球市场模块 (整合亚洲市场与欧美市场)
// 依赖: utils.js, api.js, charts.js

class AsiaMarketController {
    constructor() {
    }

    async loadData() {
        console.log('📊 加载亚洲市场数据...');

        const promises = [
            this.loadCNFearGreed(),
            this.loadCNOverboughtOversold(),
            this.loadCNIndices(),
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
            console.error('加载亚洲指数失败:', error);
            utils.renderError('asia-indices', '亚洲指数加载失败');
        }
    }

    renderCNIndices(data) {
        const container = document.getElementById('asia-indices');
        if (!container) return;

        if (data.error || !data.indices) {
            utils.renderError('asia-indices', data.error || '暂无数据');
            return;
        }

        const indices = data.indices || [];
        const formatIndexPoint = (value) => {
            if (value === null || value === undefined || isNaN(value)) return '--';
            return Number(value).toFixed(2);
        };

        let html = indices.map(item => {
            const changeVal = item.change_pct;
            const changeClass = changeVal > 0 ? 'text-up' : changeVal < 0 ? 'text-down' : '';
            const sign = changeVal > 0 ? '+' : '';
            const volHtml = (item.amount && item.amount > 0) 
                ? `<div class="index-vol">成交 ${utils.formatNumber(item.amount / 100000000)}亿</div>` 
                : `<div class="index-vol" style="visibility: hidden;">&nbsp;</div>`;

            return `
                <div class="index-item">
                    <div class="index-name">${item.name}</div>
                    <div class="index-price ${changeClass}">${formatIndexPoint(item.price)}</div>
                    <div class="index-change ${changeClass}">
                        ${sign}${formatIndexPoint(item.change_amount)} 
                        (${sign}${utils.formatPercentage(changeVal)})
                    </div>
                    ${volHtml}
                </div>
            `;
        }).join('');

        if (indices.length % 2 !== 0) {
            html += `<div class="index-item"></div>`;
        }

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

    async loadCNFearGreed() {
        try {
            const data = await api.getCNFearGreed();
            this.renderCNFearGreed(data);
        } catch (error) {
            console.error('加载恐慌贪婪指数失败:', error);
            utils.renderError('asia-fear-greed', '恐慌贪婪指数加载失败');
        }
    }

    async loadCNOverboughtOversold() {
        try {
            const data = await api.getCNOverboughtOversold();
            utils.renderOverboughtOversold('asia-obo-signal', data);
        } catch (error) {
            console.error('加载超买超卖信号失败:', error);
        }
    }

    async loadCNBonds() {
        try {
            const data = await api.getCNTreasuryYields();
            this.renderCNBonds(data);
        } catch (error) {
            console.error('加载国债数据失败:', error);
            utils.renderError('asia-bonds', '国债数据加载失败');
        }
    }

    renderCNFearGreed(data) {
        const container = document.getElementById('asia-fear-greed');
        if (!container) return;

        if (data.error) {
            utils.renderError('asia-fear-greed', data.error);
            return;
        }

        // Bind Info Button
        const infoBtn = document.getElementById('info-asia-fear');
        if (infoBtn && data.explanation) {
            infoBtn.onclick = () => utils.showInfoModal('亚洲市场情绪指数 (上证指数)', utils.buildFearGreedModalBody(data));
            infoBtn.style.display = 'flex';
        }

        // Center content
        container.style.justifyContent = 'center';

        container.innerHTML = `
            <div class="fg-gauge" id="asia-fear-greed-gauge"></div>
            <div class="fg-info" style="flex: 0 1 auto;">
                <div class="fg-level">${data.level}</div>
                <div class="fg-desc">${data.description}</div>
                <div class="fg-desc" style="font-size: 11px; color: var(--text-secondary); margin-top: 8px;">${utils.getFearGreedMetaLine(data)}</div>
            </div>
        `;

        if (window.charts) {
            setTimeout(() => {
                charts.createFearGreedGauge('asia-fear-greed-gauge', data);
            }, 100);
        }
    }

    renderCNBonds(data) {
        const container = document.getElementById('asia-bonds');
        if (!container) return;

        if (!data || data.error) {
            utils.renderError('asia-bonds', data && data.error ? data.error : '暂无数据');
            return;
        }

        if (data.status === 'warming_up') {
            utils.renderWarmingUp('asia-bonds');
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

class WesternMarketController {
    constructor() {
    }

    async loadData() {
        console.log('📊 加载欧美市场数据...');
        const promises = [
            this.loadUSFearGreed(),
            this.loadUSOverboughtOversold(),
            this.loadUSLeaders(),
            this.loadUSMarketHeat(),
            this.loadUSBondYields()
        ];
        await Promise.allSettled(promises);
    }

    async loadUSOverboughtOversold() {
        try {
            const data = await api.getUSOverboughtOversold();
            utils.renderOverboughtOversold('western-obo-signal', data);
        } catch (error) {
            console.error('加载美股超买超卖信号失败:', error);
        }
    }

    async loadUSFearGreed() {
        try {
            const data = await api.getUSCustomFearGreed();
            this.renderUSFearGreed(data);

            if (window.lucide) lucide.createIcons();
        } catch (error) {
            console.error('加载美国市场恐慌指数失败:', error);
            utils.renderError('western-fear-greed', '美国市场恐慌指数加载失败');
        }
    }

    async loadUSMarketHeat() {
        try {
            const data = await api.getUSMarketHeat();
            this.renderUSMarketHeat(data);
        } catch (error) {
            console.error('加载美国市场热度失败:', error);
            utils.renderError('market-western-heat', '美国市场热度加载失败');
        }
    }

    async loadUSBondYields() {
        try {
            const data = await api.getUSBondYields();
            this.renderUSBondYields(data);
        } catch (error) {
            console.error('加载美债数据失败:', error);
            utils.renderError('western-treasury', '美债数据加载失败');
        }
    }

    async loadUSLeaders() {
        try {
            const data = await api.getUSMarketLeaders();
            if (data._warming_up) {
                console.info('欧美主要指数数据预热中...');
                utils.renderWarmingUp('western-indices');
                this._leadersRetryCount = (this._leadersRetryCount || 0) + 1;
                if (this._leadersRetryCount <= 12 && !this._leadersRetryTimer) {
                    this._leadersRetryTimer = setTimeout(() => {
                        this._leadersRetryTimer = null;
                        this.loadUSLeaders();
                    }, 5000);
                }
                return;
            }
            this._leadersRetryCount = 0;
            if (data.error || data._error) {
                console.error('加载欧美主要指数API返回错误:', data.error || data.message);
                utils.renderError('western-indices', data.error || data.message || '主要指数加载失败');
                return;
            }
            this.renderUSLeaders(data);
        } catch (error) {
            console.error('加载欧美主要指数失败:', error);
            utils.renderError('western-indices', '主要指数加载失败');
        }
    }

    getIndicatorName(key) {
        const names = {
            volatility: '波动率',
            momentum: '动量',
            breadth: '广度',
            flow: '资金流',
            rsi: 'RSI',
            vix: 'VIX波动率',
            sp500_momentum: '标普动量',
            market_breadth: '市场分化',
            safe_haven: '避险需求',
            junk_bond_demand: '垃圾债',
            market_volatility: '波动率',
            put_call_options: '期权',
            market_momentum: '动量',
            stock_price_strength: '股价',
            stock_price_breadth: '广度',
            safe_haven_demand: '避险'
        };
        return names[key] || key;
    }

    renderUSFearGreed(data) {
        const container = document.getElementById('western-fear-greed');
        if (!container) return;

        container.style.justifyContent = 'center';

        const renderFallback = (message) => {
            let displayMsg = message;
            if (message === 'warming_up' || message === 'warming up') {
                displayMsg = '<i data-lucide="clock" width="14" style="vertical-align: middle; margin-right: 4px;"></i> 数据预热中，请稍后刷新';
            }
            container.innerHTML = `
                <div style="text-align: center; padding: 20px;">
                    <div style="margin-bottom: 12px; color: var(--text-secondary); font-size: 14px;">${displayMsg}</div>
                    <a href="https://edition.cnn.com/markets/fear-and-greed" target="_blank" class="btn-primary" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 6px; background: var(--accent-blue); color: white; text-decoration: none; font-size: 13px;">
                        CNN 官网参考
                        <i data-lucide="external-link" width="14"></i>
                    </a>
                    <div style="margin-top: 8px; font-size: 11px; color: var(--text-tertiary);">当前页面为自定义估算指数</div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        };

        if (!data || data.error) {
            renderFallback(data ? data.error : '暂无数据');
            return;
        }

        const infoBtn = document.getElementById('info-western-fear');
        if (infoBtn && data.explanation) {
            infoBtn.onclick = () => utils.showInfoModal('欧美市场情绪指数 (标普500代理)', utils.buildFearGreedModalBody(data));
            infoBtn.style.display = 'flex';
        }

        const score = data.score;
        const level = data.level || '未知';
        const indicators = data.indicators;

        if (score == null) {
            renderFallback('恐慌指数数据不可用');
            return;
        }

        let contentHtml = `
            <div class="fg-gauge" id="western-fear-greed-gauge"></div>
            <div class="fg-info" style="flex: 0 1 auto;">
                <div class="fg-level">${level}</div>
                <div class="fg-desc">${data.description || ''}</div>
                <div class="fg-desc" style="font-size: 11px; color: var(--text-secondary); margin-top: 8px;">${utils.getFearGreedMetaLine(data)}</div>
        `;

        if (indicators) {
            contentHtml += `<div class="fg-desc" style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 8px;">`;
            for (const [key, val] of Object.entries(indicators)) {
                if (typeof val !== 'object' || val.score == null) continue;
                contentHtml += `
                    <span class="heat-tag heat-gray" title="${this.getIndicatorName(key)}: ${Math.round(val.score)}">
                        ${this.getIndicatorName(key)}
                    </span>
                    `;
            }
            contentHtml += `</div>`;
        }

        contentHtml += `
            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-color); width: 100%; display: flex; justify-content: center;">
                <a href="https://edition.cnn.com/markets/fear-and-greed" target="_blank" style="display: inline-flex; align-items: center; gap: 4px; color: var(--text-secondary); text-decoration: none; font-size: 11px; transition: color 0.2s;">
                    CNN 官方参考(非同口径)
                    <i data-lucide="external-link" width="10"></i>
                </a>
            </div>
        `;

        contentHtml += '</div>';

        container.innerHTML = contentHtml;

        if (window.charts) {
            setTimeout(() => {
                charts.createFearGreedGauge('western-fear-greed-gauge', { score, level });
            }, 100);
        }
    }

    renderUSMarketHeat(data) {
        const container = document.getElementById('market-western-heat');
        if (!container) return;

        if (data && data.error) {
            container.classList.remove('heat-grid');
            utils.renderError('market-western-heat', data.error);
            return;
        }

        if (!data || !Array.isArray(data) || data.length === 0) {
            container.classList.remove('heat-grid');
            utils.renderError('market-western-heat', '暂无数据');
            return;
        }

        container.classList.add('heat-grid');

        const html = data.map(item => {
            const change = item.change_pct;
            const changeClass = change >= 0 ? 'text-up-us' : 'text-down-us';

            return `
                <div class="heat-cell">
                    <div class="item-sub">${item.name}</div>
                    <div class="heat-val ${changeClass}">${utils.formatPercentage(change)}</div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
        container.className = 'heat-grid';
    }

    renderUSBondYields(data) {
        const container = document.getElementById('western-treasury');
        if (!container) return;

        if (data && data.error) {
            utils.renderError('western-treasury', data.error);
            return;
        }

        if (!data) {
            utils.renderError('western-treasury', '暂无数据');
            return;
        }

        const infoBtn = document.getElementById('info-western-treasury');
        if (infoBtn) {
            infoBtn.onclick = () => utils.showInfoModal('美债收益率指标说明',
                `1. 10Y-2Y 利差 (衰退预警)
关注倒挂（负值）。当短期收益率高于长期时，是历史上预测衰退最准确的信号。

2. 2年期美债 (政策风向)
对美联储利率政策最敏感。大幅上涨通常意味着市场预期加息或短期降息预期落空。

3. 10年期美债 (资产定价之锚)
全球风险资产的定价基准。收益率过高(>4.5%)会显著抽走股市流动性，压低资产估值。

4. 30年期美债 (长期预期)
反映由于对长期通胀失控或国家债务规模担忧而要求的额外补偿（期限溢价）。`);
            infoBtn.style.display = 'flex';
        }

        let metrics = [];
        if (Array.isArray(data)) {
            metrics = data;
        } else if (data.metrics) {
            metrics = data.metrics;
        } else {
            utils.renderError('western-treasury', '数据格式错误');
            return;
        }

        if (metrics.length === 0) {
            utils.renderError('western-treasury', '暂无数据');
            return;
        }

        let html = `<div class="bond-scroll" style="flex-wrap: wrap;">`;

        metrics.forEach(item => {
            let changeHtml = '';
            if (item.change !== undefined) {
                const changeClass = item.change > 0 ? 'text-up-us' : item.change < 0 ? 'text-down-us' : '';
                const sign = item.change > 0 ? '+' : '';
                changeHtml = `<span class="${changeClass}" style="font-size: 12px; margin-left: 6px;">${sign}${item.change}</span>`;
            }

            let analysisHtml = '';
            if (item.analysis) {
                let color = 'var(--text-secondary)';
                if (item.analysis.level === 'danger') color = 'var(--accent-red)';
                if (item.analysis.level === 'warning') color = '#f59e0b';
                if (item.analysis.level === 'good') color = 'var(--accent-green)';

                analysisHtml = `<div style="font-size: 11px; margin-top: 6px; color: ${color}; line-height: 1.3;">${item.analysis.text}</div>`;
            }

            let valClass = '';
            if (item.is_spread) {
                valClass = item.value < 0 ? 'text-down-us' : 'text-up-us';
            }

            html += `
                <div class="bond-item" style="flex: 1 0 140px; text-align: left; padding: 12px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div class="bond-name">${item.name}</div>
                        <div style="display: flex; align-items: baseline;">
                            <span class="bond-rate ${valClass}" style="font-size: 18px;">${item.value}${item.suffix || ''}</span>
                            ${changeHtml}
                        </div>
                    </div>
                    ${analysisHtml}
                </div>
            `;
        });

        html += `</div>`;
        container.innerHTML = html;
        container.style.display = 'block';
    }

    renderUSLeaders(data) {
        const container = document.getElementById('western-indices');
        const container2 = document.getElementById('western-sp500');
        if (container2) {
            container2.style.display = 'none';
        }

        if (!container) return;

        const indices = data.indices || [];
        if (indices.length === 0) {
            container.classList.remove('heat-grid');
            container.classList.add('list-container');
            utils.renderError('western-indices', '暂无指数数据');
            return;
        }

        container.classList.remove('list-container');
        container.classList.add('heat-grid');
        container.style.gridTemplateColumns = 'repeat(2, 1fr)';

        let html = indices.map(item => {
            const changeVal = item.change_pct;
            const changeClass = changeVal > 0 ? 'text-up-us' : changeVal < 0 ? 'text-down-us' : '';
            const sign = changeVal > 0 ? '+' : '';

            const changeAmt = item.change_amount != null ? item.change_amount : (item.price * item.change_pct / 100);

            return `
                <div class="index-item">
                    <div class="index-name">${item.name}</div>
                    <div class="index-price ${changeClass}">${utils.formatNumber(item.price)}</div>
                    <div class="index-change ${changeClass}">
                        ${sign}${utils.formatNumber(changeAmt)} 
                        (${sign}${utils.formatPercentage(changeVal)})
                    </div>
                </div>
            `;
        }).join('');

        if (indices.length % 2 !== 0) {
            html += `<div class="index-item"></div>`;
        }

        container.innerHTML = html;
        container.classList.remove('loading');
    }
}

class MarketController {
    constructor() {
        this.asiaController = new AsiaMarketController();
        this.westernController = new WesternMarketController();
    }

    async loadData() {
        console.log('📊 加载全球市场数据 (亚洲市场 + 欧美市场)...');
        await Promise.allSettled([
            this.asiaController.loadData(),
            this.westernController.loadData()
        ]);
    }
}
