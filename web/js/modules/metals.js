class MetalsController {
    async loadData() {
        console.log('📊 加载有色金属数据...');

        try {
            // Load Ratio
            const ratioData = await api.getGoldSilverRatio();
            this.renderGoldSilver(ratioData);

            // Load Spot Prices
            const spotData = await api.getMetalSpotPrices();
            this.renderMetalSpotPrices(spotData);

        } catch (error) {
            console.error('加载金属数据失败:', error);
            utils.renderError('gold-silver-ratio', '金属数据加载失败');
        }
    }

    renderGoldSilver(data) {
        const container = document.getElementById('gold-silver-ratio');
        if (!container) return;

        if (data.error) {
            utils.renderError('gold-silver-ratio', data.error);
            return;
        }

        const ratio = data.ratio;
        const gold = data.gold;
        const silver = data.silver;

        // Bind Info Button
        const infoBtn = document.getElementById('info-metals-ratio');
        if (infoBtn && data.explanation) {
            infoBtn.onclick = () => utils.showInfoModal('金银比 (Gold/Silver Ratio)', data.explanation);
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

    renderMetalSpotPrices(data) {
        const container = document.getElementById('metal-prices');
        if (!container) return;

        if (!data || data.length === 0) {
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
