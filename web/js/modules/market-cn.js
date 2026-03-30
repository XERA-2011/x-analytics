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
            utils.renderOverboughtOversold('cn-obo-signal', data);
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

        // 渲染涨跌幅排行榜
        this.renderSectorRanking(data.sectors);

        // 渲染 ECharts Treemap
        if (window.charts) {
            window.charts.renderTreemap('cn-sector-heatmap', data.sectors);
        }

        // 绑定说明按钮
        const infoBtn = document.getElementById('info-cn-heatmap');
        if (infoBtn) {
            infoBtn.onclick = () => utils.showInfoModal('行业板块热力图', `热力图展示 A 股一级行业板块的结构与强弱变化。

图表口径：
• 面积代表板块总市值
• 颜色代表板块涨跌幅
• 默认使用本地一级行业映射，低频刷新；运行时只聚合实时个股行情

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

    renderSectorRanking(sectors) {
        const container = document.getElementById('cn-sector-ranking');
        if (!container || !sectors || sectors.length === 0) return;

        const renderEmptyState = (text) => `
            <div class="ranking-item" style="display:flex; align-items:center; justify-content:center; min-height:120px; color:var(--text-secondary);">
                ${text}
            </div>
        `;

        const sortedDesc = [...sectors].sort((a, b) => b.change_pct - a.change_pct);
        const positives = sortedDesc.filter(item => (item.change_pct || 0) >= 0);
        const negatives = [...sortedDesc]
            .filter(item => (item.change_pct || 0) < 0)
            .sort((a, b) => a.change_pct - b.change_pct);

        const gainers = positives.slice(0, 5);
        const losers = negatives.slice(0, 5);

        // 情绪分析函数 (与 charts.js treemap tooltip 保持一致)
        const getSentiment = (change, turnover) => {
            const t = turnover || 0;
            const c = change || 0;
            const absC = Math.abs(c);

            if (absC < 0.8) return { text: '横盘震荡', color: '#9ca3af' };

            if (c > 0) {
                if (c > 8) return t > 2 ? { text: '极度超买', color: '#dc2626' } : { text: '逼空拉升', color: '#dc2626' };
                if (t > 5 && c > 4) return { text: '严重超买', color: '#dc2626' };
                if (t > 3 || c > 4) return { text: '放量上攻', color: '#ef4444' };
                if (t < 1.2 && c < 2) return { text: '缩量上涨', color: '#f59e0b' };
                return { text: '温和上涨', color: '#ef4444' };
            } else {
                if (c < -8) return t > 2 ? { text: '恐慌抛售', color: '#16a34a' } : { text: '闷杀出局', color: '#16a34a' };
                if (t > 5 && c < -4) return { text: '恐慌抛售', color: '#16a34a' };
                if (t > 3 || c < -4) return { text: '放量杀跌', color: '#16a34a' };
                if (t < 1.2 && c > -2) return { text: '无量下跌', color: '#10b981' };
                return { text: '弱势调整', color: '#22c55e' };
            }
        };

        const resolveStockName = (item, columnType) => {
            let preferredName = columnType === 'down' ? item.lagging_stock : item.leading_stock;
            let targetStock = null;

            if (preferredName && Array.isArray(item.children)) {
                targetStock = item.children.find(s => s.name === preferredName);
            }

            if (!targetStock && Array.isArray(item.children) && item.children.length > 0) {
                const sortedChildren = [...item.children].sort((a, b) => {
                    const changeA = Number.isFinite(Number(a.change_pct)) ? Number(a.change_pct) : 0;
                    const changeB = Number.isFinite(Number(b.change_pct)) ? Number(b.change_pct) : 0;
                    return columnType === 'down' ? changeA - changeB : changeB - changeA;
                });
                targetStock = sortedChildren[0];
            }

            if (targetStock) {
                const change = Number.isFinite(Number(targetStock.change_pct)) ? Number(targetStock.change_pct) : 0;
                const sign = change > 0 ? '+' : '';
                return `${targetStock.name} <span class="${change > 0 ? 'text-up' : change < 0 ? 'text-down' : ''}">${sign}${change.toFixed(2)}%</span>`;
            } else if (preferredName) {
                return preferredName;
            }

            return '--';
        };

        const renderItem = (item, columnType) => {
            const changeVal = item.change_pct || 0;
            const changeClass = changeVal > 0 ? 'text-up' : changeVal < 0 ? 'text-down' : '';
            const sign = changeVal > 0 ? '+' : '';
            const sentiment = getSentiment(changeVal, item.turnover);
            const stockLabel = columnType === 'down' ? '领跌' : '领涨';
            const stockNameHtml = resolveStockName(item, columnType);

            return `
                <div class="ranking-item">
                    <div class="ranking-row">
                        <div class="ranking-left">
                            <span class="ranking-name">${item.name}</span>
                            <span class="ranking-turnover">${stockLabel}: ${stockNameHtml}</span>
                        </div>
                        <div class="ranking-right">
                            <span class="ranking-change ${changeClass}">${sign}${changeVal.toFixed(2)}%</span>
                            <span class="ranking-sentiment" style="color:${sentiment.color}">${sentiment.text}</span>
                        </div>
                    </div>
                </div>
            `;
        };

        container.innerHTML = `
            <div class="ranking-column">
                <div class="ranking-header up">📈 涨幅榜</div>
                ${gainers.length > 0 ? gainers.map(item => renderItem(item, 'up')).join('') : renderEmptyState('暂无上涨行业')}
            </div>
            <div class="ranking-column">
                <div class="ranking-header down">📉 跌幅榜</div>
                ${losers.length > 0 ? losers.map(item => renderItem(item, 'down')).join('') : renderEmptyState('暂无下跌行业')}
            </div>
        `;
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
            infoBtn.onclick = () => utils.showInfoModal('中国市场情绪指数', utils.buildFearGreedModalBody(data));
            infoBtn.style.display = 'flex';
        }

        // Center content
        container.style.justifyContent = 'center';

        container.innerHTML = `
            <div class="fg-gauge" id="cn-fear-greed-gauge"></div>
            <div class="fg-info" style="flex: 0 1 auto;">

                <div class="fg-level">${data.level}</div>
                <div class="fg-desc">${data.description}</div>
                <div class="fg-desc" style="font-size: 11px; color: var(--text-secondary); margin-top: 8px;">${utils.getFearGreedMetaLine(data)}</div>
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
