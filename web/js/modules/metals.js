class MetalsController {
    async loadData() {
        console.log('📊 加载有色金属数据...');

        const promises = [
            api.getGoldSilverRatio().then(data => this.renderGoldSilver(data)),
            api.getMetalSpotPrices().then(data => this.renderMetalSpotPrices(data)),
            api.getGoldFearGreed().then(data => this.renderGoldFearGreed(data)),
            api.getSilverFearGreed().then(data => this.renderSilverFearGreed(data)),
            api.getGoldOverboughtOversold().then(data => utils.renderOverboughtOversold('gold-obo-signal', data)),
            api.getSilverOverboughtOversold().then(data => utils.renderOverboughtOversold('silver-obo-signal', data))
        ];

        await Promise.allSettled(promises);
    }



    renderGoldSilver(data) {
        const container = document.getElementById('gold-silver-ratio');
        if (!container) return;

        if (data.error) {
            if (data._warming_up) {
                utils.renderWarmingUp('gold-silver-ratio');
            } else {
                utils.renderError('gold-silver-ratio', data.message || data.error);
            }
            return;
        }

        // Clear warming up timer on successful data load
        utils.clearWarmingUpTimer('gold-silver-ratio');

        const ratio = data.ratio;
        // const gold = data.gold; // Unused
        // const silver = data.silver; // Unused

        // Bind Info Button
        const infoBtn = document.getElementById('info-metals-ratio');
        if (infoBtn && data.explanation) {
            infoBtn.onclick = () => utils.showInfoModal('金银比 (Gold/Silver Ratio)', data.explanation);
            infoBtn.style.display = 'flex';
        }

        const advice = ratio.investment_advice;

        const html = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; width: 100%;">
                <div style="font-size: 48px; font-weight: 700; line-height: 1; margin-bottom: 8px;">${ratio.current || '--'}</div>
                
                <div style="font-size: 14px; color: var(--text-secondary); margin-bottom: ${advice ? '12px' : '24px'}; padding: 4px 12px; background: var(--bg-secondary); border-radius: 12px;">
                    ${ratio.analysis ? `${ratio.analysis.level} · ${ratio.analysis.comment}` : '--'}
                </div>

                ${advice ? `
                <div style="text-align: center; margin-bottom: 24px; padding: 0 16px;">
                    <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
                        💡 ${advice.strategy}
                    </div>
                    <div style="font-size: 11px; color: var(--text-secondary);">
                        ${advice.reasoning}
                    </div>
                </div>
                ` : ''}
                
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; width: 100%; text-align: center; gap: 8px; border-top: 1px solid var(--border-color); padding-top: 16px;">
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">历史最高</div>
                        <div style="font-weight: 600;">${ratio.historical_high || '--'}</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">历史均值</div>
                        <div style="font-weight: 600;">${ratio.historical_avg || '--'}</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">历史最低</div>
                        <div style="font-weight: 600;">${ratio.historical_low || '--'}</div>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    renderGoldFearGreed(data) {
        this.renderMetalFearGreed(data, 'gold');
    }

    renderSilverFearGreed(data) {
        this.renderMetalFearGreed(data, 'silver');
    }

    renderMetalFearGreed(data, metal) {
        const container = document.getElementById(`${metal}-fear-greed`);
        const indicatorsContainer = document.getElementById(`${metal}-indicators`);

        if (!container) return;

        if (data.error) {
            const msg = data._warming_up ? '数据预热中，请稍后刷新' : data.message || data.error;
            utils.renderError(`${metal}-fear-greed`, msg);
            if (indicatorsContainer) indicatorsContainer.innerHTML = '';
            return;
        }

        // Bind Info Button
        const infoBtn = document.getElementById(`info-${metal}-fear`);
        if (infoBtn && data.explanation) {
            const title = metal === 'gold' ? '黄金恐慌贪婪指数' : '白银恐慌贪婪指数';
            infoBtn.onclick = () => utils.showInfoModal(title, data.explanation);
            infoBtn.style.display = 'flex';
        }

        // Render Gauge + Info (Unified Style)
        // Note: container is .fg-container, which has flex-direction: column and centered align

        container.innerHTML = `
            <div class="fg-gauge" id="${metal}-gauge"></div>
            <div class="fg-info" style="flex: 0 1 auto;">
                <div class="fg-level">${data.level}</div>
                <div class="fg-desc">${data.description || ''}</div>
            </div>
        `;

        // Render Gauge Chart
        if (window.charts) {
            setTimeout(() => {
                charts.createFearGreedGauge(`${metal}-gauge`, {
                    score: data.score,
                    level: data.level
                });
            }, 100);
        }

        // Render Indicators (Keep existing logic or minimal update)
        if (indicatorsContainer && data.indicators) {
            this.renderMetalIndicators(indicatorsContainer, data.indicators);
        }
    }

    renderMetalIndicators(container, indicators) {
        const items = Object.values(indicators);

        const html = items.map(item => {
            // Determine color based on score
            // Low score = Fear (Green/Down), High score = Greed (Red/Up)
            // But this is just "contribution to fear/greed", so let's just use neutral or heat colors suitable for the theme

            // Using heat-cell style
            // item.name, item.value, item.score

            let valueText = item.value;
            // Add % if likely percentage
            if (['momentum', 'trend', 'volatility', 'rsi'].some(k => item.name.toLowerCase().includes(k))) {
                // Heuristic: already formatted in backend likely? No, backend sends float
                // But check name. Actually backend sends `value`.
            }

            return `
                <div class="heat-cell" style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 12px; background: var(--bg-secondary); border-radius: 8px;">
                    <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 4px;">${item.name}</div>
                    <div style="font-size: 16px; font-weight: 600;">${item.value}</div>
                    <div style="font-size: 10px; color: var(--text-secondary); opacity: 0.7;">Score: ${item.score}</div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
        container.style.display = 'grid';
        container.style.gridTemplateColumns = '1fr 1fr';
        container.style.gap = '8px';
    }

    renderMetalSpotPrices(data) {
        const container = document.getElementById('metal-prices');
        if (!container) return;

        // Handle error/warming_up response
        if (data && data.error) {
            const msg = data._warming_up ? '数据预热中，请稍后刷新' : data.message || data.error;
            utils.renderError('metal-prices', msg);
            return;
        }

        if (!data || !Array.isArray(data) || data.length === 0) {
            utils.renderError('metal-prices', '暂无数据');
            return;
        }

        const html = data.map(item => {
            const change = utils.formatChange(item.change_pct);
            return `
                <div class="list-item">
                    <div class="item-main">
                        <span class="item-title">${item.name}</span>
                        <span class="item-sub">${item.unit}</span>
                    </div>
                    <div style="text-align: right;">
                        <div class="item-value">$${utils.formatNumber(item.price)}</div>
                        <div class="item-change ${change.class}">${change.text}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }
}
