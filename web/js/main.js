// 主应用程序

class App {
    constructor() {
        this.currentTab = 'market-cn';
        this.refreshIntervals = new Map();
        this.lastUpdateTime = null;
        this.isOnline = navigator.onLine;
        this.isRefreshing = false; // 防止重复刷新

        this.init();
    }

    async init() {
        console.log('🚀 x-analytics v2.0 启动中...');

        // 设置事件监听器
        this.setupEventListeners();

        // 设置网络状态监听
        this.setupNetworkListeners();

        // 初始化标签切换
        this.initTabSwitching();

        // 初始化卡片标签切换
        this.initCardTabs();

        // 初始化工具提示
        this.initTooltips();

        // 加载初始数据
        await this.loadInitialData();

        // 设置自动刷新
        this.setupAutoRefresh();

        console.log('✅ x-analytics v2.0 启动完成');
    }

    setupEventListeners() {
        // 窗口大小变化
        window.addEventListener('resize', utils.debounce(() => {
            if (window.charts) {
                window.charts.resize();
            }
        }, 250));

        // 页面可见性变化
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseAutoRefresh();
            } else {
                this.resumeAutoRefresh();
            }
        });

        // 键盘快捷键
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey || event.metaKey) {
                switch (event.key) {
                    case 'r':
                        event.preventDefault();
                        this.refreshCurrentTab();
                        break;
                    case '1':
                        event.preventDefault();
                        this.switchTab('market-cn');
                        break;
                    case '2':
                        event.preventDefault();
                        this.switchTab('market-us');
                        break;
                    case '3':
                        event.preventDefault();
                        this.switchTab('metals');
                        break;
                }
            }
        });
    }

    setupNetworkListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateNetworkStatus();
            this.refreshCurrentTab();
            utils.showNotification('网络连接已恢复', 'success');
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateNetworkStatus();
            utils.showNotification('网络连接已断开', 'warning');
        });
    }

    updateNetworkStatus() {
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) {
            const statusText = statusIndicator.querySelector('span:last-child');
            if (this.isOnline) {
                statusText.textContent = '实时';
                statusIndicator.style.color = 'var(--success-color)';
            } else {
                statusText.textContent = '离线';
                statusIndicator.style.color = 'var(--danger-color)';
            }
        }
    }

    initTabSwitching() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;
                this.switchTab(tabId);
            });
        });
    }

    switchTab(tabId) {
        // 更新按钮状态
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });

        // 更新内容显示
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === tabId);
        });

        this.currentTab = tabId;

        // 更新URL
        utils.setUrlParam('tab', tabId);

        // 刷新当前标签数据
        this.refreshCurrentTab();
    }

    initCardTabs() {
        const cardTabs = document.querySelectorAll('.card-tab');

        cardTabs.forEach(tab => {
            tab.addEventListener('click', (event) => {
                event.preventDefault();

                const targetId = tab.dataset.target;
                const card = tab.closest('.card');

                if (!card || !targetId) {
                    console.log('Card tab click: missing card or targetId', { card, targetId });
                    return;
                }

                console.log('Card tab clicked:', targetId);

                // 更新标签状态 - 在同一个card中的所有tabs
                card.querySelectorAll('.card-tab').forEach(t => {
                    t.classList.remove('active');
                });
                tab.classList.add('active');

                // 更新内容显示 - 在同一个card中查找所有内容容器
                card.querySelectorAll('.leaders-list, .fear-greed-container, [id^="us-"], [id^="cn-"]').forEach(content => {
                    content.classList.remove('active');
                });

                // 激活目标元素
                const targetElement = card.querySelector(`#${targetId}`);
                if (targetElement) {
                    targetElement.classList.add('active');
                    console.log('Activated target element:', targetId);
                } else {
                    console.error('Target element not found:', targetId);
                }
            });
        });
    }

    initTooltips() {
        const infoButtons = document.querySelectorAll('.info-btn');
        const tooltip = document.getElementById('tooltip');

        if (!tooltip) return;

        infoButtons.forEach(btn => {
            const showTooltip = (event) => {
                const text = btn.dataset.tooltip;
                if (!text) return;

                tooltip.textContent = text;
                tooltip.classList.add('show');

                const rect = btn.getBoundingClientRect();
                tooltip.style.left = `${rect.left + rect.width / 2}px`;
                tooltip.style.top = `${rect.top - 10}px`;
                tooltip.style.transform = 'translate(-50%, -100%)';
            };

            const hideTooltip = () => {
                tooltip.classList.remove('show');
            };

            if (utils.isTouchDevice()) {
                btn.addEventListener('click', (event) => {
                    event.stopPropagation();
                    showTooltip(event);
                    setTimeout(hideTooltip, 3000);
                });
                document.addEventListener('click', hideTooltip);
            } else {
                btn.addEventListener('mouseenter', showTooltip);
                btn.addEventListener('mouseleave', hideTooltip);
            }
        });
    }

    async loadInitialData() {
        // 从URL参数获取初始标签
        const urlTab = utils.getUrlParam('tab');
        if (urlTab && ['market-cn', 'market-us', 'metals'].includes(urlTab)) {
            // 只更新UI状态，不触发数据加载
            this.currentTab = urlTab;

            // 更新按钮状态
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.tab === urlTab);
            });

            // 更新内容显示
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.toggle('active', content.id === urlTab);
            });

            // 更新URL
            utils.setUrlParam('tab', urlTab);
        }

        // 加载当前标签数据（只调用一次）
        await this.refreshCurrentTab();
    }

    async refreshCurrentTab() {
        if (!this.isOnline) {
            console.log('离线状态，跳过数据刷新');
            return;
        }

        // 防止重复调用
        if (this.isRefreshing) {
            console.log('数据刷新中，跳过重复请求');
            return;
        }

        this.isRefreshing = true;

        try {
            switch (this.currentTab) {
                case 'market-cn':
                    await this.loadCNMarketData();
                    break;
                case 'market-us':
                    await this.loadUSMarketData();
                    break;
                case 'metals':
                    await this.loadMetalsData();
                    break;
            }

            this.updateGlobalTime();
        } catch (error) {
            console.error('刷新数据失败:', error);
            utils.showNotification('数据刷新失败', 'error');
        } finally {
            this.isRefreshing = false;
        }
    }

    async loadCNMarketData() {
        console.log('📊 加载沪港深市场数据...');

        // 并行加载所有数据
        const promises = [
            this.loadCNFearGreed(),
            this.loadCNLeaders(),
            this.loadCNMarketHeat(),
            this.loadCNDividend(),
            this.loadCNBonds()
        ];

        await Promise.allSettled(promises);
    }

    async loadCNFearGreed() {
        try {
            const data = await api.getCNFearGreed();
            this.renderCNFearGreed(data);
        } catch (error) {
            console.error('加载恐慌贪婪指数失败:', error);
            this.renderError('cn-fear-greed', '恐慌贪婪指数加载失败');
        }
    }

    async loadCNLeaders() {
        try {
            const [gainers, losers] = await Promise.all([
                api.getCNTopGainers(),
                api.getCNTopLosers()
            ]);

            this.renderCNLeaders(gainers, losers);
        } catch (error) {
            console.error('加载领涨领跌板块失败:', error);
            this.renderError('cn-gainers', '领涨领跌板块加载失败');
        }
    }

    async loadCNMarketHeat() {
        try {
            const data = await api.getCNMarketHeat();
            this.renderCNMarketHeat(data);
        } catch (error) {
            console.error('加载市场热度失败:', error);
            this.renderError('market-cn-heat', '市场热度加载失败');
        }
    }

    async loadCNDividend() {
        try {
            const data = await api.getCNDividendStocks();
            this.renderCNDividend(data);
        } catch (error) {
            console.error('加载红利低波数据失败:', error);
            this.renderError('cn-dividend', '红利低波数据加载失败');
        }
    }

    async loadCNBonds() {
        try {
            const data = await api.getCNTreasuryYields();
            this.renderCNBonds(data);
        } catch (error) {
            console.error('加载国债数据失败:', error);
            this.renderError('cn-bonds', '国债数据加载失败');
        }
    }

    async loadUSMarketData() {
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

            // Re-init icons
            if (window.lucide) lucide.createIcons();

        } catch (error) {
            console.error('加载美股恐慌指数失败:', error);
            this.renderError('us-cnn-fear', '美股恐慌指数加载失败');
        }
    }

    async loadUSMarketHeat() {
        try {
            const data = await api.getUSMarketHeat();
            this.renderUSMarketHeat(data);
        } catch (error) {
            console.error('加载美股热度失败:', error);
            this.renderError('market-us-heat', '美股热度加载失败');
        }
    }

    async loadUSBondYields() {
        try {
            const data = await api.getUSBondYields();
            this.renderUSBondYields(data);
        } catch (error) {
            console.error('加载美债数据失败:', error);
            this.renderError('us-treasury', '美债数据加载失败');
        }
    }

    async loadUSLeaders() {
        try {
            const data = await api.getUSMarketLeaders();
            if (data.error) {
                console.error('加载美股领涨板块API返回错误:', data.error);
                this.renderError('us-gainers', '排行数据暂时不可用');
                this.renderError('us-sp500', '排行数据暂时不可用');
                return;
            }
            this.renderUSLeaders(data);
        } catch (error) {
            console.error('加载美股领涨板块失败:', error);
            this.renderError('us-gainers', '排行榜加载失败');
        }
    }

    renderUSFearGreed(data, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!data || data.error) {
            container.innerHTML = '<div class="placeholder"><p>暂无数据</p></div>';
            return;
        }

        const score = data.current_value || data.score || 50;
        const level = data.current_level || data.level || '中性';
        const date = data.date ? data.date.substring(0, 10) : '';
        const indicators = data.indicators;

        let contentHtml = `
            <div class="fear-greed-display">
                <div class="fg-score class-${this.getScoreClass(score)}">${score}</div>
                <div class="fg-level">${level}</div>
        `;

        if (indicators) {
            let indicatorsHtml = '<div class="fg-indicators">';
            for (const [key, val] of Object.entries(indicators)) {
                indicatorsHtml += `
                    <div class="fg-badge">
                        <span>${this.getIndicatorName(key)}</span>
                        <span class="${utils.formatChange(val.score - 50).class}">${Math.round(val.score)}</span>
                    </div>
                 `;
            }
            indicatorsHtml += '</div>';
            contentHtml += indicatorsHtml;
        } else {
            contentHtml += `
                <div class="fg-meta">
                    <span>日变动: ${utils.formatChange(data.change_1d || 0).text}</span>
                    <span>更新: ${date}</span>
                </div>
             `;
        }

        contentHtml += '</div>';
        container.innerHTML = contentHtml;
    }

    getScoreClass(score) {
        if (score >= 75) return 'extreme-greed';
        if (score >= 55) return 'greed';
        if (score <= 25) return 'extreme-fear';
        if (score <= 45) return 'fear';
        return 'neutral';
    }

    renderUSMarketHeat(data) {
        const container = document.getElementById('market-us-heat');
        if (!container) return;

        if (!data || data.length === 0) {
            this.renderError('market-us-heat', '暂无数据');
            return;
        }

        const html = data.map(item => {
            const change = item.change_pct;
            // Determine background intensity based on change magnitude
            const intensity = Math.min(Math.abs(change) * 15, 60) + 10;
            const colorVar = change >= 0 ? `rgba(34, 197, 94, ${intensity / 100})` : `rgba(239, 68, 68, ${intensity / 100})`;

            return `
                <div class="heat-block" style="background-color: ${colorVar}">
                    <div class="heat-name" title="${item.name}">${item.name}</div>
                    <div class="heat-val">${utils.formatPercentage(change)}</div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
        container.className = 'market-heat-container us-heat-grid'; // Ensure grid layout if needed
    }

    renderUSBondYields(data) {
        const container = document.getElementById('us-treasury');
        if (!container) return;

        if (!data || data.length === 0) {
            this.renderError('us-treasury', '暂无数据');
            return;
        }

        const html = data.map(item => {
            let valClass = '';
            if (item.is_spread) {
                valClass = item.value < 0 ? 'text-down' : 'text-up';
            }
            return `
                <div class="bond-item">
                    <span class="bond-name">${item.name}</span>
                    <span class="bond-val ${valClass}">${item.value}${item.suffix || ''}</span>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    renderUSLeaders(data) {
        // 使用第一个容器渲染指数
        const container = document.getElementById('us-gainers'); // 复用现有容器ID
        const container2 = document.getElementById('us-sp500');  // 隐藏或清理这个容器

        if (container2) {
            container2.style.display = 'none'; // 仅隐藏第二个容器
            // 将第一个Tab改名为 "三大指数"
            const tabBtn = document.querySelector('.card-tab[data-target="us-gainers"]');
            if (tabBtn) {
                tabBtn.textContent = '三大指数';
                // 隐藏其他Tab按钮
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
            const change = utils.formatChange(index.change_pct);
            return `
                <div class="stock-item index-item">
                    <div class="stock-info">
                        <div class="stock-name" style="font-size: 1.1em; font-weight: bold;">${index.name}</div>
                        <div class="stock-code" style="color: #888;">${index.code}</div>
                    </div>
                    <div class="stock-metrics">
                        <div class="stock-price" style="font-size: 1.1em;">${Number(index.price).toFixed(2)}</div>
                        <div class="stock-change ${change.class}">${change.text}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
        container.classList.add('us-indices-grid');

        // Note: renderUSStockList is no longer used by this method
    }

    renderUSStockList(containerId, groupData) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const stocks = groupData.gainers || [];
        if (stocks.length === 0) {
            container.innerHTML = '<div class="placeholder"><p>暂无数据</p></div>';
            return;
        }

        const html = stocks.map(stock => {
            const change = utils.formatChange(stock.change_pct);
            return `
                <div class="stock-item">
                    <div class="stock-info">
                        <div class="stock-name" title="${stock.name}">${stock.name}</div>
                        <div class="stock-code">${stock.code}</div>
                    </div>
                    <div class="stock-metrics">
                        <div class="stock-price">$${utils.formatNumber(stock.price)}</div>
                        <div class="stock-change ${change.class}">${change.text}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    async loadMetalsData() {
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
            this.renderError('gold-silver-ratio', '金属数据加载失败');
        }
    }

    renderMetalSpotPrices(data) {
        const container = document.getElementById('metal-prices');
        if (!container) return;

        if (!data || data.length === 0) {
            this.renderError('metal-prices', '暂无现货数据');
            return;
        }

        const html = `
            <table class="simple-table">
                <thead>
                    <tr>
                        <th>名称</th>
                        <th>价格</th>
                        <th>单位</th>
                        <th>涨跌幅</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(item => `
                        <tr>
                            <td>${item.name}</td>
                            <td>${utils.formatNumber(item.price)}</td>
                            <td>${item.unit}</td>
                            <td class="${utils.formatChange(item.change_pct).class}">${utils.formatChange(item.change_pct).text}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        container.innerHTML = html;
    }

    // 渲染方法
    renderCNFearGreed(data) {
        const container = document.getElementById('cn-fear-greed');
        if (!container) return;

        if (data.error) {
            this.renderError('cn-fear-greed', data.error);
            return;
        }

        // 创建仪表盘
        const gaugeContainer = document.createElement('div');
        gaugeContainer.className = 'fear-greed-gauge';
        gaugeContainer.id = 'cn-fear-greed-gauge';

        // 创建信息显示
        const infoContainer = document.createElement('div');
        infoContainer.className = 'fear-greed-info';
        infoContainer.innerHTML = `
            <div class="fear-greed-score" style="color: ${this.getFearGreedColor(data.score)}">${data.score}</div>
            <div class="fear-greed-level">${data.level}</div>
            <div class="fear-greed-description">${data.description}</div>
        `;

        container.innerHTML = '';
        container.appendChild(gaugeContainer);
        container.appendChild(infoContainer);

        // 创建图表
        setTimeout(() => {
            charts.createFearGreedGauge('cn-fear-greed-gauge', data);
        }, 100);
    }

    renderCNLeaders(gainers, losers) {
        this.renderSectorList('cn-gainers', gainers.sectors || []);
        this.renderSectorList('cn-losers', losers.sectors || []);
    }

    renderSectorList(containerId, sectors) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!sectors || sectors.length === 0) {
            container.innerHTML = '<div class="placeholder"><p>暂无数据</p></div>';
            return;
        }

        const html = sectors.map(sector => {
            const change = utils.formatChange(sector.change_pct);
            return `
                <div class="stock-item">
                    <div class="stock-info">
                        <div class="stock-name">${sector.name}</div>
                        <div class="stock-code">
                            ${sector.stock_count}家公司 | 
                            ${sector.leading_stock ? `领涨: ${sector.leading_stock}` : ''}
                        </div>
                    </div>
                    <div class="stock-metrics">
                        <div class="stock-price">${utils.formatNumber(sector.total_market_cap / 100000000)}亿</div>
                        <div class="stock-change ${change.class}">${change.text}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    renderCNMarketHeat(data) {
        const container = document.getElementById('market-cn-heat');
        if (!container) return;

        if (data.error) {
            this.renderError('market-cn-heat', data.error);
            return;
        }

        const html = `
            <div class="heat-score-section">
                <div class="heat-score" style="color: ${this.getHeatColor(data.heat_score)}">${data.heat_score}</div>
                <div class="heat-level">${data.heat_level}</div>
            </div>
            <div class="heat-metrics">
                <div class="heat-metric">
                    <div class="metric-label">成交额</div>
                    <div class="metric-value">${utils.formatNumber(data.total_turnover)}亿</div>
                </div>
                <div class="heat-metric">
                    <div class="metric-label">涨跌比</div>
                    <div class="metric-value">${data.rise_fall_ratio}</div>
                </div>
                <div class="heat-metric">
                    <div class="metric-label">强势股</div>
                    <div class="metric-value">${data.strong_stocks}</div>
                </div>
                <div class="heat-metric">
                    <div class="metric-label">活跃度</div>
                    <div class="metric-value">${data.activity_level}</div>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    renderCNDividend(data) {
        const container = document.getElementById('cn-dividend');
        if (!container) return;

        if (data.error || !data.stocks) {
            this.renderError('cn-dividend', data.error || '暂无数据');
            return;
        }

        const stats = data.strategy_stats || {};
        const html = `
            <div class="dividend-stats">
                <div class="dividend-stat">
                    <div class="stat-label">平均股息率</div>
                    <div class="stat-value">${utils.formatPercentage(stats.avg_dividend_yield)}</div>
                </div>
                <div class="dividend-stat">
                    <div class="stat-label">平均PE</div>
                    <div class="stat-value">${utils.formatNumber(stats.avg_pe_ratio)}</div>
                </div>
                <div class="dividend-stat">
                    <div class="stat-label">低波动股</div>
                    <div class="stat-value">${stats.low_volatility_count || 0}</div>
                </div>
            </div>
            <div class="dividend-stocks">
                ${data.stocks.slice(0, 10).map(stock => `
                    <div class="dividend-stock">
                        <div class="dividend-info">
                            <div class="dividend-name">${stock.name}</div>
                            <div class="dividend-code">${stock.code}</div>
                        </div>
                        <div class="dividend-metrics">
                            <div class="dividend-yield">${utils.formatPercentage(stock.estimated_dividend_yield)}</div>
                            <div class="dividend-pe">PE ${utils.formatNumber(stock.pe_ratio)}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        container.innerHTML = html;
    }

    renderCNBonds(data) {
        const container = document.getElementById('cn-bonds');
        if (!container) return;

        if (data.error) {
            this.renderError('cn-bonds', data.error);
            return;
        }

        const yieldCurve = data.yield_curve || {};
        const keyRates = data.key_rates || {};

        const html = `
            <div class="yield-curve">
                ${Object.entries(yieldCurve).map(([period, rate]) => {
            const change = data.yield_changes?.[period] || 0;
            const changeClass = change > 0 ? 'positive' : change < 0 ? 'negative' : '';
            return `
                        <div class="yield-item">
                            <div class="yield-period">${period.toUpperCase()}</div>
                            <div class="yield-rate">${utils.formatPercentage(rate)}</div>
                            <div class="yield-change ${changeClass}">
                                ${change > 0 ? '+' : ''}${utils.formatNumber(change, 3)}
                            </div>
                        </div>
                    `;
        }).join('')}
            </div>
            <div class="bond-analysis">
                <div class="analysis-title">10年期国债: ${utils.formatPercentage(keyRates['10y'])}</div>
                <div class="analysis-content">
                    期限利差 (10Y-2Y): ${utils.formatNumber(keyRates.spread_10y_2y, 3)}%
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    renderGoldSilverRatio(data) {
        const container = document.getElementById('gold-silver-ratio');
        if (!container) return;

        if (data.error) {
            this.renderError('gold-silver-ratio', data.error);
            return;
        }

        const ratio = data.ratio || {};
        const gold = data.gold || {};
        const silver = data.silver || {};

        const html = `
            <div class="ratio-display">
                <div class="ratio-value" style="color: ${this.getRatioColor(ratio.current)}">${ratio.current}</div>
                <div class="ratio-level">${ratio.analysis?.level || '--'}</div>
                <div class="ratio-comment">${ratio.analysis?.comment || '--'}</div>
            </div>
            <div class="metal-prices">
                <div class="metal-price">
                    <div class="metal-name">黄金</div>
                    <div class="metal-value">$${utils.formatNumber(gold.price)}</div>
                    <div class="metal-change ${gold.change_pct > 0 ? 'positive' : 'negative'}">
                        ${gold.change_pct > 0 ? '+' : ''}${utils.formatPercentage(gold.change_pct)}
                    </div>
                </div>
                <div class="metal-price">
                    <div class="metal-name">白银</div>
                    <div class="metal-value">$${utils.formatNumber(silver.price)}</div>
                    <div class="metal-change ${silver.change_pct > 0 ? 'positive' : 'negative'}">
                        ${silver.change_pct > 0 ? '+' : ''}${utils.formatPercentage(silver.change_pct)}
                    </div>
                </div>
            </div>
            ${ratio.investment_advice ? `
                <div class="investment-advice">
                    <div class="advice-title">投资建议</div>
                    <div class="advice-content">
                        推荐金属: <span class="advice-strategy">${ratio.investment_advice.preferred_metal}</span><br>
                        策略: ${ratio.investment_advice.strategy}<br>
                        ${ratio.investment_advice.reasoning}
                    </div>
                </div>
            ` : ''}
        `;

        container.innerHTML = html;
    }

    renderError(containerId, message) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = `
            <div class="placeholder">
                <i data-lucide="alert-circle"></i>
                <p>${message}</p>
            </div>
        `;

        // 重新初始化图标
        if (window.lucide) {
            lucide.createIcons();
        }
    }

    // 工具方法
    getFearGreedColor(score) {
        if (score >= 80) return '#ef4444';
        if (score >= 65) return '#f59e0b';
        if (score >= 55) return '#eab308';
        if (score >= 45) return '#6b7280';
        if (score >= 35) return '#3b82f6';
        if (score >= 20) return '#8b5cf6';
        return '#10b981';
    }

    getHeatColor(score) {
        if (score >= 80) return '#ef4444';
        if (score >= 65) return '#f59e0b';
        if (score >= 55) return '#eab308';
        if (score >= 45) return '#6b7280';
        return '#3b82f6';
    }

    getRatioColor(ratio) {
        if (ratio > 85) return '#10b981'; // 绿色 - 白银便宜
        if (ratio < 65) return '#f59e0b'; // 橙色 - 黄金便宜
        return '#6b7280'; // 灰色 - 正常
    }

    getIndicatorName(key) {
        const names = {
            vix: 'VIX',
            sp500_momentum: 'SP500动量',
            market_breadth: '市场广度',
            safe_haven: '避险需求'
        };
        return names[key] || key;
    }

    updateGlobalTime() {
        const now = new Date();
        const timeString = utils.formatTime(now);

        // 更新所有时间显示
        const timeElements = document.querySelectorAll('#global-update-time, #footer-update-time');
        timeElements.forEach(el => {
            if (el) el.textContent = timeString;
        });

        this.lastUpdateTime = now;
    }

    setupAutoRefresh() {
        // 清除现有定时器
        this.refreshIntervals.forEach(interval => clearInterval(interval));
        this.refreshIntervals.clear();

        // 设置不同频率的刷新
        const intervals = {
            'market-cn': 30000,  // 30秒
            'market-us': 60000,  // 1分钟
            'metals': 300000     // 5分钟
        };

        Object.entries(intervals).forEach(([tab, interval]) => {
            const timer = setInterval(() => {
                if (this.currentTab === tab && this.isOnline && !document.hidden) {
                    this.refreshCurrentTab();
                }
            }, interval);

            this.refreshIntervals.set(tab, timer);
        });
    }

    pauseAutoRefresh() {
        this.refreshIntervals.forEach(interval => clearInterval(interval));
    }

    resumeAutoRefresh() {
        this.setupAutoRefresh();
        this.refreshCurrentTab();
    }
}

// 启动应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});