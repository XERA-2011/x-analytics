class HKMarketController {
    constructor() {
    }

    async loadData() {
        console.log('📊 加载香港市场数据...');
        await Promise.allSettled([
            this.loadHKIndices(),
            this.loadHKFearGreed(),
            this.loadHKOverboughtOversold()
        ]);
    }

    async loadHKOverboughtOversold() {
        try {
            const data = await api.getHKOverboughtOversold();
            this.renderOverboughtOversold('hk-obo-signal', data);
        } catch (error) {
            console.error('加载港股超买超卖信号失败:', error);
        }
    }

    renderOverboughtOversold(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (data.error || data._warming_up) {
            container.innerHTML = `<div class="obo-loading">信号计算中...</div>`;
            return;
        }

        const signalClass = data.signal === 'overbought' ? 'obo-overbought' :
            data.signal === 'oversold' ? 'obo-oversold' : 'obo-neutral';
        const signalText = data.level || '中性';
        const strength = data.strength || 50;

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
            // utils.renderError('hk-gainers', '数据加载失败');
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
        if (infoBtn && data.description) {
            infoBtn.onclick = () => utils.showInfoModal('港股恐慌贪婪指数', data.description);
            infoBtn.style.display = 'flex';
        }

        // Use flex: 0 1 auto to prevent stretching, allowing justify-content: center to work on the parent
        let contentHtml = `
            <div class="fg-gauge" id="hk-fear-gauge"></div>
            <div class="fg-info" style="flex: 0 1 auto;">

                <div class="fg-level">${level}</div>
        `;

        if (indicators) {
            contentHtml += `<div class="fg-desc" style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;">`;
            // RSI
            if (indicators.rsi_14) {
                contentHtml += `
                    <span class="heat-tag heat-gray" title="RSI (14)">
                       RSI: ${indicators.rsi_14.score}
                    </span>
                 `;
            }
            // Bias
            if (indicators.bias_60) {
                contentHtml += `
                    <span class="heat-tag heat-gray" title="偏离度 (60日)">
                       Bias: ${indicators.bias_60.value}
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

        // Ensure grid layout matches US style (rely on css class .heat-grid)
        // container.style.display = 'grid'; // Removed to use CSS class
    }
}
