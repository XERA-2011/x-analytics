class MetalsController {
    async loadData() {
        console.log('📊 加载有色金属数据...');

        try {
            // Load Ratio
            const ratioData = await api.getGoldSilverRatio();
            this.renderGoldSilverRatio(ratioData);

            // Load Spot Prices
            const spotData = await api.getMetalSpotPrices();
            this.renderMetalSpotPrices(spotData);

        } catch (error) {
            console.error('加载金属数据失败:', error);
            utils.renderError('gold-silver-ratio', '金属数据加载失败');
        }
    }

    renderGoldSilverRatio(data) {
        const container = document.getElementById('gold-silver-ratio');
        if (!container) return;

        if (data.error) {
            utils.renderError('gold-silver-ratio', data.error);
            return;
        }

        const ratio = data.ratio || {};
        const gold = data.gold || {};
        const silver = data.silver || {};

        const goldChange = utils.formatChange(gold.change_pct);
        const silverChange = utils.formatChange(silver.change_pct);

        const html = `
            <div style="display: flex; flex-direction: column; gap: 16px; width: 100%; max-width: 400px; margin: 0 auto;">
                <!-- 1. 比值核心展示 -->
                <div style="text-align: center;">
                    <div class="fg-score" style="color: ${utils.getRatioColor(ratio.current)}; font-size: 42px;">${ratio.current}</div>
                    <div class="fg-level">${ratio.analysis?.level || '--'}</div>
                    <div class="item-sub" style="margin-top: 4px;">${ratio.analysis?.comment || ''}</div>
                </div>

                <!-- 2. 价格展示 (左右分栏) -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div style="background: var(--bg-subtle); padding: 12px; border-radius: 6px; text-align: center;">
                        <div class="item-sub" style="margin-bottom: 4px;">黄金</div>
                        <div class="heat-val" style="font-size: 16px;">$${utils.formatNumber(gold.price)}</div>
                        <div class="${goldChange.class}" style="font-size: 12px; margin-top: 2px;">${goldChange.text}</div>
                    </div>
                    <div style="background: var(--bg-subtle); padding: 12px; border-radius: 6px; text-align: center;">
                        <div class="item-sub" style="margin-bottom: 4px;">白银</div>
                        <div class="heat-val" style="font-size: 16px;">$${utils.formatNumber(silver.price)}</div>
                        <div class="${silverChange.class}" style="font-size: 12px; margin-top: 2px;">${silverChange.text}</div>
                    </div>
                </div>

                <!-- 3. 历史数据 (三列) -->
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center; background: var(--bg-subtle); padding: 12px; border-radius: 6px;">
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
