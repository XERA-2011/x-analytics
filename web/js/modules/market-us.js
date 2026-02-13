class USMarketController {
    constructor() {
        this._hasStaleData = false;
        this._retried = false;
    }

    async loadData() {
        console.log('📊 加载美国市场数据...');
        this._hasStaleData = false;
        const promises = [
            this.loadUSFearGreed(),
            this.loadUSOverboughtOversold(),
            this.loadUSLeaders(),
            this.loadUSMarketHeat(),
            this.loadUSBondYields()
        ];
        await Promise.allSettled(promises);

        // Stale data auto-retry: backend is refreshing in background, wait then reload once
        if (this._hasStaleData && !this._retried) {
            this._retried = true;
            console.log('🔄 检测到过期数据，5秒后自动刷新...');
            setTimeout(() => {
                api.clearLocalCache();
                this.loadData();
            }, 5000);
        } else {
            this._retried = false;
        }
    }

    async loadUSOverboughtOversold() {
        try {
            const data = await api.getUSOverboughtOversold();
            if (data && data._stale) this._hasStaleData = true;
            utils.renderOverboughtOversold('us-obo-signal', data);
        } catch (error) {
            console.error('加载美股超买超卖信号失败:', error);
        }
    }



    async loadUSFearGreed() {
        try {
            // Load only custom data (CNN direct fetch is deprecated/banned)
            const data = await api.getUSCustomFearGreed();
            if (data && data._stale) this._hasStaleData = true;
            this.renderUSFearGreed(data);

            if (window.lucide) lucide.createIcons();

        } catch (error) {
            console.error('加载美国市场恐慌指数失败:', error);
            utils.renderError('us-cnn-fear', '美国市场恐慌指数加载失败');
        }
    }

    async loadUSMarketHeat() {
        try {
            const data = await api.getUSMarketHeat();
            if (data && data._stale) this._hasStaleData = true;
            this.renderUSMarketHeat(data);
        } catch (error) {
            console.error('加载美国市场热度失败:', error);
            utils.renderError('market-us-heat', '美国市场热度加载失败');
        }
    }

    async loadUSBondYields() {
        try {
            const data = await api.getUSBondYields();
            if (data && data._stale) this._hasStaleData = true;
            this.renderUSBondYields(data);
        } catch (error) {
            console.error('加载美债数据失败:', error);
            utils.renderError('us-treasury', '美债数据加载失败');
        }
    }

    async loadUSLeaders() {
        try {
            const data = await api.getUSMarketLeaders();
            if (data && data._stale) this._hasStaleData = true;
            if (data.error) {
                console.error('加载美国市场领涨板块API返回错误:', data.error);
                utils.renderError('us-gainers', '排行数据暂时不可用');
                return;
            }
            this.renderUSLeaders(data);
        } catch (error) {
            console.error('加载美国市场领涨板块失败:', error);
            utils.renderError('us-gainers', '排行榜加载失败');
        }
    }

    getIndicatorName(key) {
        const names = {
            // Backend keys
            vix: 'VIX波动率',
            sp500_momentum: '标普动量',
            market_breadth: '市场分化',
            safe_haven: '避险需求',

            // Legacy/CNN concept keys
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
        const container = document.getElementById('us-cnn-fear');
        if (!container) return;

        // Center content
        container.style.justifyContent = 'center';

        const renderFallback = (message) => {
            container.innerHTML = `
                <div style="text-align: center; padding: 20px;">
                    <div style="margin-bottom: 12px; color: var(--text-secondary); font-size: 14px;">${message}</div>
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

        // Bind Info Button
        const infoBtn = document.getElementById('info-us-cnn');
        if (infoBtn && data.explanation) {
            infoBtn.onclick = () => utils.showInfoModal('恐慌贪婪指数', data.explanation);
            infoBtn.style.display = 'flex';
        }

        const score = data.score;
        const level = data.level || '未知';
        const indicators = data.indicators;

        // 如果没有分数，显示Fallback
        if (score == null) {
            renderFallback('恐慌指数数据不可用');
            return;
        }

        let contentHtml = `
            <div class="fg-gauge" id="us-cnn-gauge"></div>
            <div class="fg-info" style="flex: 0 1 auto;">
                <div class="fg-level">${level}</div>
                <div class="fg-desc">${data.description || ''}</div>
        `;

        // Add indicators if available (using unified 'heat-tag' style)
        if (indicators) {
            contentHtml += `<div class="fg-desc" style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 8px;">`;
            for (const [key, val] of Object.entries(indicators)) {
                if (typeof val !== 'object' || !val.score) continue;
                contentHtml += `
                    <span class="heat-tag heat-gray" title="${this.getIndicatorName(key)}: ${Math.round(val.score)}">
                        ${this.getIndicatorName(key)}
                    </span>
                    `;
            }
            contentHtml += `</div>`;
        }

        // Add permanent CNN link (reference only)
        contentHtml += `
            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-color); width: 100%; display: flex; justify-content: center;">
                <a href="https://edition.cnn.com/markets/fear-and-greed" target="_blank" style="display: inline-flex; align-items: center; gap: 4px; color: var(--text-secondary); text-decoration: none; font-size: 11px; transition: color 0.2s;">
                    CNN 官网参考
                    <i data-lucide="external-link" width="10"></i>
                </a>
            </div>
        `;

        contentHtml += '</div>'; // Close fg-info

        container.innerHTML = contentHtml;

        if (window.charts) {
            setTimeout(() => {
                charts.createFearGreedGauge('us-cnn-gauge', { score, level });
            }, 100);
        }
    }

    renderUSMarketHeat(data) {
        const container = document.getElementById('market-us-heat');
        if (!container) return;

        // Handle error/warming_up response
        if (data && data.error) {
            container.classList.remove('heat-grid');
            utils.renderError('market-us-heat', data.error);
            return;
        }

        if (!data || !Array.isArray(data) || data.length === 0) {
            container.classList.remove('heat-grid');
            utils.renderError('market-us-heat', '暂无数据');
            return;
        }

        // Restore grid layout
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
        const container = document.getElementById('us-treasury');
        if (!container) return;

        // Handle error/warming_up response
        if (data && data.error) {
            utils.renderError('us-treasury', data.error);
            return;
        }

        if (!data) {
            utils.renderError('us-treasury', '暂无数据');
            return;
        }

        // Bind Info Button
        const infoBtn = document.getElementById('info-us-treasury');
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
            utils.renderError('us-treasury', '数据格式错误');
            return;
        }

        if (metrics.length === 0) {
            utils.renderError('us-treasury', '暂无数据');
            return;
        }

        // Render using bond-scroll layout but optimized for analysis text
        // Force flex-wrap to ensure it forms a grid-like structure on mobile
        let html = `<div class="bond-scroll" style="flex-wrap: wrap;">`;

        metrics.forEach(item => {
            let changeHtml = '';
            if (item.change !== undefined) {
                // US Market: usually Green Up, Red Down for prices, but for yields?
                // Visual consistency: If yields go UP (Bad for stocks), maybe Red? 
                // But let's stick to standard math: + is Green, - is Red (or local habit).
                // Actually standard project rule: US Market = Green Up.
                const changeClass = item.change > 0 ? 'text-up-us' : item.change < 0 ? 'text-down-us' : '';
                const sign = item.change > 0 ? '+' : '';
                changeHtml = `<span class="${changeClass}" style="font-size: 12px; margin-left: 6px;">${sign}${item.change}</span>`;
            }

            // Analysis Color
            let analysisHtml = '';
            if (item.analysis) {
                let color = 'var(--text-secondary)';
                if (item.analysis.level === 'danger') color = 'var(--accent-red)';
                if (item.analysis.level === 'warning') color = '#f59e0b'; // Amber
                if (item.analysis.level === 'good') color = 'var(--accent-green)';

                analysisHtml = `<div style="font-size: 11px; margin-top: 6px; color: ${color}; line-height: 1.3;">${item.analysis.text}</div>`;
            }

            // Highlighting Spreads
            let valClass = '';
            if (item.is_spread) {
                valClass = item.value < 0 ? 'text-down-us' : 'text-up-us';
                // Override changeHtml for spread often doesn't have daily change in this simple API
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
        const container = document.getElementById('us-gainers');

        // Hide compatibility container if exists
        const container2 = document.getElementById('us-sp500');
        if (container2) {
            container2.style.display = 'none';
        }

        if (!container) return;

        const indices = data.indices || [];
        if (indices.length === 0) {
            container.classList.remove('heat-grid');
            container.classList.add('list-container');
            utils.renderError('us-gainers', '暂无指数数据');
            return;
        }

        // Switch to grid layout
        container.classList.remove('list-container');
        container.classList.add('heat-grid');
        container.style.gridTemplateColumns = 'repeat(2, 1fr)';

        const html = indices.map(item => {
            const changeVal = item.change_pct;
            // US Colors: Green Up, Red Down (Handled by styles.css logic via classes? 
            // text-up-us is green, text-down-us is red.
            // But wait, CN/HK uses text-up (Red), text-down (Green).
            // US Market requires specific color logic.
            // utils.formatChange uses 'us' param to switch colors.
            // But here I am constructing manually.
            const changeClass = changeVal > 0 ? 'text-up-us' : changeVal < 0 ? 'text-down-us' : '';
            const sign = changeVal > 0 ? '+' : '';

            // Should verify if change_amount exists, if not calculate or hide
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

        container.innerHTML = html;
        container.classList.remove('loading');
    }
}
