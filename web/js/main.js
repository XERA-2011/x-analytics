// 主应用程序
// 依赖: utils.js, api.js, charts.js, modules/*.js

class App {
    constructor() {
        this.currentTab = 'market-cn';
        this.lastUpdateTime = null;
        this.isRefreshing = false;
        this.loadedTabs = new Set();

        // Controllers
        this.modules = {
            'market-cn': new CNMarketController(),
            'market-hk': new HKMarketController(),
            'market-us': new USMarketController(),
            'metals': new MetalsController()
        };

        this.init();
    }

    async init() {
        console.log('🚀 x-analytics 启动中...');

        // 设置事件监听器
        this.setupEventListeners();

        // 初始化标签切换
        this.initTabSwitching();

        // 初始化卡片标签切换
        this.initCardTabs();

        // 初始化工具提示
        this.initTooltips();

        // 加载初始数据
        await this.loadInitialData();

        console.log('✅ x-analytics 启动完成');
    }

    setupEventListeners() {
        // 窗口大小变化
        window.addEventListener('resize', utils.debounce(() => {
            if (window.charts) {
                window.charts.resize();
            }
        }, 250));

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

    initTabSwitching() {
        const tabButtons = document.querySelectorAll('.tab-btn');
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

        // 懒加载：仅首次切换到该 Tab 时加载数据
        if (!this.loadedTabs.has(tabId)) {
            this.refreshCurrentTab();
        }
    }

    initCardTabs() {
        const cardTabs = document.querySelectorAll('.card-tab');
        cardTabs.forEach(tab => {
            tab.addEventListener('click', (event) => {
                event.preventDefault();
                const targetId = tab.dataset.target;
                const card = tab.closest('.card');

                if (!card || !targetId) {
                    return;
                }

                // 更新标签状态
                card.querySelectorAll('.card-tab').forEach(t => {
                    t.classList.remove('active');
                });
                tab.classList.add('active');

                // 更新内容显示
                card.querySelectorAll('.fear-greed-container, [id^="us-"], [id^="cn-"]').forEach(content => {
                    content.classList.remove('active');
                });

                // 激活目标元素
                const targetElement = card.querySelector(`#${targetId}`);
                if (targetElement) {
                    targetElement.classList.add('active');
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
        const urlTab = utils.getUrlParam('tab');
        if (urlTab && ['market-cn', 'market-hk', 'market-us', 'metals'].includes(urlTab)) {
            this.switchTab(urlTab); // This calls refreshCurrentTab inside
        } else {
            // Default load
            await this.refreshCurrentTab();
        }
    }

    async refreshCurrentTab() {
        if (!navigator.onLine) {
            console.log('离线状态，跳过数据刷新');
            return;
        }

        if (this.isRefreshing) {
            console.log('数据刷新中，跳过重复请求');
            return;
        }

        this.isRefreshing = true;

        // 清除前端缓存，确保手动刷新时获取最新数据
        api.clearLocalCache();

        // UI Loading State (Button)
        const activeTab = document.querySelector('.tab-content.active');
        const refreshBtn = activeTab ? activeTab.querySelector('.refresh-btn') : null;
        let originalText = '';

        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.classList.add('refreshing');
            const icon = refreshBtn.querySelector('i');
            if (icon) icon.classList.add('spin');
            originalText = refreshBtn.innerHTML;
            refreshBtn.innerHTML = '<i data-lucide="loader-2" class="spin" width="14"></i> 刷新中...';
            if (window.lucide) lucide.createIcons();
        }

        try {
            // Delegate to Module
            const controller = this.modules[this.currentTab];
            if (controller) {
                await controller.loadData();
            } else {
                console.error('No controller found for tab:', this.currentTab);
            }

            this.loadedTabs.add(this.currentTab);
            this.updateGlobalTime();
        } catch (error) {
            console.error('刷新数据失败:', error);
        } finally {
            this.isRefreshing = false;

            if (refreshBtn && originalText) {
                setTimeout(() => {
                    refreshBtn.disabled = false;
                    refreshBtn.classList.remove('refreshing');
                    refreshBtn.innerHTML = originalText;
                    if (window.lucide) lucide.createIcons();
                }, 500);
            }
        }
    }

    updateGlobalTime() {
        const timeElement = document.getElementById('global-update-time');
        const footerTimeElement = document.getElementById('footer-update-time');
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { hour12: false });

        if (timeElement) timeElement.textContent = `Updated: ${timeStr}`;
        if (footerTimeElement) footerTimeElement.textContent = utils.formatDate(now);

        this.lastUpdateTime = now;
    }
}

// Global App Instance
window.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});