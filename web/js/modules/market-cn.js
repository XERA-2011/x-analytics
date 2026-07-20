class CNMarketController {
    constructor() {
    }

    async loadData() {
        console.log('📊 加载中国市场与香港市场数据...');

        const promises = [
            this.loadCNFearGreed(),
            this.loadCNOverboughtOversold(),
            this.loadCNIndices(),
            this.loadCNBonds(),
            this.loadLPR(),
            this.loadHKIndices(),
            this.loadHKFearGreed(),
            this.loadHKOverboughtOversold()
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
        const formatIndexPoint = (value) => {
            if (value === null || value === undefined || isNaN(value)) return '--';
            return Number(value).toFixed(2);
        };

        const html = indices.map(item => {
            const changeVal = item.change_pct;
            const changeClass = changeVal > 0 ? 'text-up' : changeVal < 0 ? 'text-down' : '';
            const sign = changeVal > 0 ? '+' : '';

            return `
                <div class="index-item">
                    <div class="index-name">${item.name}</div>
                    <div class="index-price ${changeClass}">${formatIndexPoint(item.price)}</div>
                    <div class="index-change ${changeClass}">
                        ${sign}${formatIndexPoint(item.change_amount)} 
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
    // 香港市场
    // =========================================================================
    async loadHKOverboughtOversold() {
        try {
            const data = await api.getHKOverboughtOversold();
            utils.renderOverboughtOversold('hk-obo-signal', data);
        } catch (error) {
            console.error('加载港股超买超卖信号失败:', error);
        }
    }

    async loadHKIndices() {
        try {
            let data = await api.getHKIndices();

            // 修复：处理可能的多层嵌套 (data.data)
            if (data && data.data && (data.indices === undefined)) {
                console.log('检测到嵌套数据结构，正在解包...');
                data = data.data;
            }

            this.renderHKIndices(data.indices);
            this.renderHKSectors(data.sectors);
        } catch (error) {
            console.error('加载港股数据失败:', error);
            utils.renderError('hk-indices', '港股数据加载失败');
            const sectorContainer = document.getElementById('hk-sectors-all');
            if (sectorContainer) utils.renderError('hk-sectors-all', '数据加载失败');
        }
    }

    async loadHKFearGreed() {
        try {
            let data = await api.getHKFearGreed();

            // 修复：处理可能的多层嵌套
            if (data && data.data && (data.score === undefined && data.error === undefined)) {
                data = data.data;
            }

            this.renderHKFearGreed(data);
        } catch (error) {
            console.error('加载港股恐慌指数失败:', error);
            utils.renderError('hk-fear-greed', '恐慌指数加载失败');
        }
    }

    renderHKFearGreed(data) {
        const container = document.getElementById('hk-fear-greed');
        if (!container) return;

        // Ensure container centers its content group
        container.style.justifyContent = 'center';

        if (data && data.error) {
            utils.renderError('hk-fear-greed', data.error);
            return;
        }

        const score = data.score;
        // 如果没有分数，显示错误
        if (score == null) {
            utils.renderError('hk-fear-greed', '暂无数值');
            return;
        }

        const level = data.level || '未知';
        const indicators = data.indicators;

        // 绑定说明弹窗
        const infoBtn = document.getElementById('info-hk-fear');
        if (infoBtn && (data.explanation || data.description)) {
            infoBtn.onclick = () => utils.showInfoModal('香港市场情绪指数', utils.buildFearGreedModalBody(data) || data.description);
            infoBtn.style.display = 'flex';
        }

        // Use flex: 0 1 auto to prevent stretching, allowing justify-content: center to work on the parent
        let contentHtml = `
            <div class="fg-gauge" id="hk-fear-gauge"></div>
            <div class="fg-info" style="flex: 0 1 auto;">

                <div class="fg-level">${level}</div>
                <div class="fg-desc" style="font-size: 11px; color: var(--text-secondary); margin-top: 8px;">${utils.getFearGreedMetaLine(data)}</div>
        `;

        if (indicators) {
            contentHtml += `<div class="fg-desc" style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;">`;
            if (indicators.rsi) {
                contentHtml += `
                    <span class="heat-tag heat-gray" title="RSI (14)">
                       RSI: ${indicators.rsi.score}
                    </span>
                 `;
            }
            if (indicators.momentum) {
                contentHtml += `
                    <span class="heat-tag heat-gray" title="偏离度 (60日)">
                       动量: ${indicators.momentum.value}%
                    </span>
                 `;
            }
            contentHtml += `</div>`;
        }

        contentHtml += '</div>';
        container.innerHTML = contentHtml;

        if (window.charts) {
            setTimeout(() => {
                charts.createFearGreedGauge('hk-fear-gauge', { score: score, level: level });
            }, 100);
        }
    }

    renderHKIndices(indices) {
        const container = document.getElementById('hk-indices');
        if (!container) return;

        if (!indices || indices.length === 0) {
            utils.renderError('hk-indices', '暂无指数数据');
            return;
        }

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
                </div>
            `;
        }).join('');

        container.innerHTML = html;
        container.classList.remove('loading');
    }

    renderHKSectors(sectorsData) {
        const container = document.getElementById('hk-sectors-all');
        if (!container) return;

        if (!sectorsData || !sectorsData.all) {
            utils.renderError('hk-sectors-all', '暂无板块数据');
            return;
        }

        // Sort by change_pct desc
        const list = sectorsData.all.sort((a, b) => b.change_pct - a.change_pct);

        const html = list.map(item => {
            const change = utils.formatChange(item.change_pct);

            // 模仿 US Market Heat 样式 (更简洁)
            return `
                <div class="heat-cell">
                    <div class="item-sub" title="${item.code}">${item.name}</div>
                    <div class="heat-val ${change.class}">${change.text}</div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
        container.classList.remove('loading');
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
