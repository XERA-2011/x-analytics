class CNMarketController {
    constructor() {
    }

    async loadData() {
        console.log('📊 加载中国市场数据...');

        const promises = [
            this.loadCNFearGreed(),
            this.loadCNOverboughtOversold(),
            this.loadCNIndices(),
            this.loadSectorHeatmap(), // 新增: 加载全市场热力图

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



    async loadCNFearGreed() {
        try {
            const data = await api.getCNFearGreed();
            this.renderCNFearGreed(data);
        } catch (error) {
            console.error('加载恐慌贪婪指数失败:', error);
            utils.renderError('cn-fear-greed', '恐慌贪婪指数加载失败');
        }
    }

    async loadCNOverboughtOversold() {
        try {
            const data = await api.getCNOverboughtOversold();
            this.renderOverboughtOversold('cn-obo-signal', data);
        } catch (error) {
            console.error('加载超买超卖信号失败:', error);
            // 不影响主流程，静默失败
        }
    }

    renderOverboughtOversold(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (data.error || data._warming_up) {
            container.innerHTML = `<div class="obo-loading">信号计算中...</div>`;
            return;
        }

        const signalClass = utils.getOboClass(data);
        const signalText = data.level || '中性';
        const strength = data.strength || 50;

        // 生成简化的指标标签
        const indicators = data.indicators || {};
        const tags = [];
        if (indicators.rsi && !indicators.rsi.error) {
            tags.push(`RSI:${Math.round(indicators.rsi.value)}`);
        }
        if (indicators.macd && !indicators.macd.error) {
            const macdSign = indicators.macd.histogram > 0 ? '+' : '-';
            tags.push(`MACD:${macdSign}`);
        }
        if (indicators.bollinger && !indicators.bollinger.error) {
            const bollPos = indicators.bollinger.position > 0.5 ? '▲' :
                indicators.bollinger.position < -0.5 ? '▼' : '―';
            tags.push(`布林:${bollPos}`);
        }
        if (indicators.kdj && !indicators.kdj.error) {
            const kdjSignal = indicators.kdj.k > 80 ? '▲' : indicators.kdj.k < 20 ? '▼' : 'N';
            tags.push(`KDJ:${kdjSignal}`);
        }

        container.innerHTML = `
            <div class="obo-signal ${signalClass}">
                <span class="obo-label">技术信号</span>
                <span class="obo-level">${signalText}</span>
                <span class="obo-strength">${strength.toFixed(1)}</span>
            </div>
            <div class="obo-tags">
                ${tags.map(t => `<span class="heat-tag heat-gray">${t}</span>`).join('')}
            </div>
        `;
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

    // =========================================================================
    // 全市场热力图
    // =========================================================================
    async loadSectorHeatmap() {
        try {
            const data = await api.request("/market-cn/sectors/all");
            this.renderSectorHeatmap(data);
        } catch (error) {
            console.error('加载全市场板块失败:', error);
            utils.renderError('cn-sector-heatmap', '加载失败');
        }
    }

    renderSectorHeatmap(data) {
        if (!data || data.error || !data.sectors) {
            utils.renderError('cn-sector-heatmap', data?.error || '暂无数据');
            return;
        }

        // 渲染 ECharts Treemap
        if (window.charts) {
            window.charts.renderTreemap('cn-sector-heatmap', data.sectors);
        }

        // 绑定说明按钮
        const infoBtn = document.getElementById('info-cn-heatmap');
        if (infoBtn) {
            infoBtn.onclick = () => utils.showInfoModal('全行业热力图', `热力图展示 A 股全行业板块的实时涨跌情况，方块大小代表板块市值。

**情绪分析逻辑**（基于换手率+涨跌幅）：

📈 上涨情况：
• 极度超买：涨幅>8% + 换手>2%（情绪极度亢奋，追高风险极大）
• 逼空拉升：涨幅>8% + 换手<2%（筹码高度集中，主力控盘拉升）
• 严重超买：涨幅>4% + 换手>5%（放量大涨，短期获利盘丰厚）
• 放量上攻：涨幅>4% 或 换手>3%（多头占优，量价配合需观察）
• 缩量上涨：涨幅<2% + 换手<1.2%（持股惜售，上攻动能偏弱）
• 温和上涨：其他上涨情况（常态运行，无明显异动）

📉 下跌情况：
• 恐慌抛售：跌幅>8% + 换手>2%（多杀多踩踏，恐慌情绪蔓延）
• 闷杀出局：跌幅>8% + 换手<2%（抛盘稀少仍大跌，无人承接）
• 放量杀跌：跌幅>4% 或 换手>3%（空方主导，抛压较重）
• 无量下跌：跌幅<2% + 换手<1.2%（交投萎缩，市场信心不足）
• 弱势调整：其他下跌情况（技术性回调，可关注支撑位）

📊 其他：
• 横盘震荡：涨跌幅<0.8%（多空僵持，等待突破方向）`);
            infoBtn.style.display = 'flex';
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
