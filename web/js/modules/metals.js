class MetalsController {
    async loadData() {
        console.log('📊 加载有色金属数据...');

        const promises = [
            api.getGoldSilverRatio().then(data => this.renderGoldSilver(data)),
            api.getMetalSpotPrices().then(data => this.renderMetalSpotPrices(data)),
            api.getGoldFearGreed().then(data => this.renderGoldFearGreed(data)),
            api.getGoldOverboughtOversold().then(data => utils.renderOverboughtOversold('gold-obo-signal', data))
        ];

        await Promise.allSettled(promises);

        // Bind Info Button
        const infoBtn = document.getElementById('info-gold-heat');
        if (infoBtn) {
            infoBtn.onclick = () => {
                utils.showInfoModal('黄金技术热度指标说明', `
<div style="font-family: var(--font-sans); color: var(--text-primary); line-height: 1.6;">
    <p style="font-size: 14px; margin-bottom: 16px;">黄金技术热度指数（0-100）是一个综合技术面指标，评估黄金当前在技术面上的超买/超卖热度。数值越高代表市场越偏向超买（高热），越低代表越偏向超卖（低热）。</p>
    
    <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 8px;">1. 核心计算因子与权重</h4>
    <ul style="margin: 0 0 16px 20px; padding: 0;">
        <li style="margin-bottom: 6px;"><b>RSI (30%)</b>：14 日相对强弱指标，反映短期价格超买超卖强弱。</li>
        <li style="margin-bottom: 6px;"><b>均线偏离度 (30%)</b>：当前价格相对 50 日均线 (MA50) 的偏离百分比，衡量趋势偏离度。</li>
        <li style="margin-bottom: 6px;"><b>波动率趋势 (20%)</b>：当前 20 日波动率对比历史 60 日波动均值，反映波动率变化。</li>
        <li style="margin-bottom: 6px;"><b>当日涨跌 (20%)</b>：当日价格的百分比变动幅度。</li>
    </ul>

    <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 8px;">2. 计算与归一化逻辑</h4>
    <ul style="margin: 0 0 16px 20px; padding: 0;">
        <li style="margin-bottom: 6px;">每个因子通过公式映射转换为 0-100 的“因子得分”后，按权重加权求和得出仪表盘的<b>综合热度分（0-100）</b>。</li>
        <li style="margin-bottom: 6px;"><b>“近一年分位数”</b>是通过回溯过去 250 个交易日的历史综合热度序列，计算当前分数处于历史水位的百分比（例如 89% 表示当前比过去 89% 的时间都更热）。</li>
    </ul>

    <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 8px;">3. 下方“技术信号”强弱条</h4>
    <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">技术信号条（如“强烈超买 76.8”）为另一个独立的<b>多因子强弱模型</b>，融合了 MACD、KDJ、布林带等更广泛的技术因子判定，提供更敏捷的对照验证。</p>

    <p style="font-size: 11px; color: var(--text-secondary); font-style: italic; border-top: 1px solid var(--border-light); padding-top: 12px; margin: 0;">免责声明：本数据仅供参考，不构成任何投资买卖建议。</p>
</div>
                `);
            };
            infoBtn.style.display = 'flex';
        }
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

    renderMetalFearGreed(data, metal) {
        const container = document.getElementById(`${metal}-fear-greed`);

        if (!container) return;

        if (data.error) {
            const msg = data._warming_up ? '数据预热中，请稍后刷新' : data.message || data.error;
            utils.renderError(`${metal}-fear-greed`, msg);
            return;
        }

        // Render Gauge + Info (Unified Style)
        // Note: container is .fg-container, which has flex-direction: column and centered align

        container.innerHTML = `
            <div class="fg-gauge" id="${metal}-gauge"></div>
            <div class="fg-info" style="flex: 0 1 auto; width: 100%;">
                <div class="fg-level">${data.level}</div>
                <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin: 6px 0;">近一年分位数: ${data.percentile != null ? data.percentile + '%' : '--'}</div>
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
