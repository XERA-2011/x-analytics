class USMarketController {
    async loadData() {
        console.log('📊 加载美股市场数据...');
        const promises = [
            this.loadUSFearGreed(),
            this.loadUSLeaders(),
            this.loadUSMarketHeat(),
            this.loadUSBondYields()
        ];
        await Promise.allSettled(promises);
    }

    async loadUSFearGreed() {
        try {
            // Load CNN
            const cnnData = await api.getUSFearGreed();
            this.renderUSFearGreed(cnnData, 'us-cnn-fear');

            // Load Custom
            const customData = await api.getUSCustomFearGreed();
            this.renderUSFearGreed(customData, 'us-custom-fear');

            if (window.lucide) lucide.createIcons();

        } catch (error) {
            console.error('加载美股恐慌指数失败:', error);
            utils.renderError('us-cnn-fear', '美股恐慌指数加载失败');
        }
    }

    async loadUSMarketHeat() {
        try {
            const data = await api.getUSMarketHeat();
            this.renderUSMarketHeat(data);
        } catch (error) {
            console.error('加载美股热度失败:', error);
            utils.renderError('market-us-heat', '美股热度加载失败');
        }
    }

    async loadUSBondYields() {
        try {
            const data = await api.getUSBondYields();
            this.renderUSBondYields(data);
        } catch (error) {
            console.error('加载美债数据失败:', error);
            utils.renderError('us-treasury', '美债数据加载失败');
        }
    }

    async loadUSLeaders() {
        try {
            const data = await api.getUSMarketLeaders();
            if (data.error) {
                console.error('加载美股领涨板块API返回错误:', data.error);
                utils.renderError('us-gainers', '排行数据暂时不可用');
                return;
            }
            this.renderUSLeaders(data);
        } catch (error) {
            console.error('加载美股领涨板块失败:', error);
            utils.renderError('us-gainers', '排行榜加载失败');
        }
    }

    renderUSFearGreed(data, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!data || data.error) {
            container.innerHTML = '<div class="loading">暂无数据</div>';
            return;
        }

        const score = data.current_value || data.score || 50;
        const level = data.current_level || data.level || '中性';
        const indicators = data.indicators;

        let contentHtml = `
            <div class="fg-gauge" id="${containerId}-gauge"></div>
            <div class="fg-info">
                <div class="fg-score class-${utils.getScoreClass(score)}">${score}</div>
                <div class="fg-level">${level}</div>
        `;

        if (indicators) {
            contentHtml += `<div class="fg-desc" style="display: flex; flex-wrap: wrap; gap: 4px; justify-content: center;">`;
            for (const [key, val] of Object.entries(indicators)) {
                contentHtml += `
                    <span class="badge" title="${this.getIndicatorName(key)}">
                       ${Math.round(val.score)}
                    </span>
                 `;
            }
            contentHtml += `</div>`;
        } else {
            contentHtml += `
                <div class="fg-desc">
                    变动: ${utils.formatChange(data.change_1d || 0, 2, 'us').text}
                </div>
             `;
        }

        contentHtml += '</div>';

        container.innerHTML = contentHtml;

        if (window.charts) {
            setTimeout(() => {
                charts.createFearGreedGauge(`${containerId}-gauge`, { score: score, level: level });
            }, 100);
        }
    }

    // Helper for indicator names
    getIndicatorName(key) {
        const names = {
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

    renderUSMarketHeat(data) {
        const container = document.getElementById('market-us-heat');
        if (!container) return;

        if (!data || data.length === 0) {
            utils.renderError('market-us-heat', '暂无数据');
            return;
        }

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

        if (!data || data.length === 0) {
            utils.renderError('us-treasury', '暂无数据');
            return;
        }

        const html = `
            <div class="bond-scroll">
                ${data.map(item => {
            let valClass = '';
            if (item.is_spread) {
                valClass = item.value < 0 ? 'text-down' : 'text-up';
            }
            return `
                        <div class="bond-item">
                            <span class="bond-name">${item.name}</span>
                            <span class="bond-rate ${valClass}">${item.value}${item.suffix || ''}</span>
                        </div>
                    `;
        }).join('')}
            </div>
        `;

        container.innerHTML = html;
    }

    renderUSLeaders(data) {
        const container = document.getElementById('us-gainers');

        // Hide compatibility container if exists
        const container2 = document.getElementById('us-sp500');
        if (container2) {
            container2.style.display = 'none';
            // Update tab button if exists
            const tabBtn = document.querySelector('.card-tab[data-target="us-gainers"]');
            if (tabBtn) {
                tabBtn.textContent = '三大指数';
                const siblings = tabBtn.parentElement.children;
                for (let i = 0; i < siblings.length; i++) {
                    if (siblings[i] !== tabBtn) siblings[i].style.display = 'none';
                }
            }
        }

        if (!container) return;

        const indices = data.indices || [];
        if (indices.length === 0) {
            container.innerHTML = '<div class="placeholder"><p>暂无指数数据</p></div>';
            return;
        }

        const html = indices.map(index => {
            const change = utils.formatChange(index.change_pct, 2, 'us');
            return `
                <div class="list-item">
                    <div class="item-main">
                        <span class="item-title">${index.name}</span>
                        <span class="item-sub">${index.code}</span>
                    </div>
                    <div style="text-align: right;">
                        <div class="item-value">${Number(index.price).toFixed(2)}</div>
                        <div class="item-change ${change.class}">${change.text}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }
}
