// 移动端交互优化

class MobileOptimizer {
    constructor() {
        this.init();
    }

    init() {
        this.setupTouchHandlers();
        this.setupViewportHandler();
        this.setupOrientationHandler();
        this.setupScrollOptimization();
    }

    // 设置触摸处理
    setupTouchHandlers() {
        // 防止双击缩放
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (event) => {
            const now = (new Date()).getTime();
            if (now - lastTouchEnd <= 300) {
                event.preventDefault();
            }
            lastTouchEnd = now;
        }, false);

        // 优化触摸反馈
        document.addEventListener('touchstart', (event) => {
            const target = event.target.closest('.tab-btn, .card-tab, .info-btn');
            if (target) {
                target.style.transform = 'scale(0.95)';
                target.style.transition = 'transform 0.1s ease-out';
            }
        });

        document.addEventListener('touchend', (event) => {
            const target = event.target.closest('.tab-btn, .card-tab, .info-btn');
            if (target) {
                setTimeout(() => {
                    target.style.transform = '';
                    target.style.transition = '';
                }, 100);
            }
        });
    }

    // 设置视口处理
    setupViewportHandler() {
        // 处理移动端视口高度变化（如虚拟键盘弹出）
        const setViewportHeight = () => {
            const vh = window.innerHeight * 0.01;
            document.documentElement.style.setProperty('--vh', `${vh}px`);
        };

        setViewportHeight();
        window.addEventListener('resize', utils.debounce(setViewportHeight, 100));
        window.addEventListener('orientationchange', () => {
            setTimeout(setViewportHeight, 100);
        });
    }

    // 设置屏幕方向处理
    setupOrientationHandler() {
        const handleOrientationChange = () => {
            // 横屏时调整布局
            const isLandscape = window.innerWidth > window.innerHeight;
            document.body.classList.toggle('landscape', isLandscape);
            
            // 重新调整图表大小
            if (window.charts) {
                setTimeout(() => {
                    window.charts.resize();
                }, 200);
            }
        };

        window.addEventListener('orientationchange', () => {
            setTimeout(handleOrientationChange, 100);
        });
        
        window.addEventListener('resize', utils.debounce(handleOrientationChange, 100));
    }

    // 设置滚动优化
    setupScrollOptimization() {
        // 平滑滚动到顶部
        this.addScrollToTop();
        
        // 优化滚动性能
        let ticking = false;
        const updateScrollPosition = () => {
            const scrollTop = window.pageYOffset;
            
            // 更新导航栏样式
            const navbar = document.querySelector('.navbar');
            if (navbar) {
                navbar.classList.toggle('scrolled', scrollTop > 10);
            }
            
            ticking = false;
        };

        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(updateScrollPosition);
                ticking = true;
            }
        });
    }

    // 添加回到顶部按钮
    addScrollToTop() {
        const scrollToTopBtn = document.createElement('button');
        scrollToTopBtn.className = 'scroll-to-top';
        scrollToTopBtn.innerHTML = '<i data-lucide="chevron-up"></i>';
        scrollToTopBtn.setAttribute('aria-label', '回到顶部');
        
        // 添加样式
        Object.assign(scrollToTopBtn.style, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            border: 'none',
            backgroundColor: 'var(--primary-color)',
            color: 'white',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'var(--shadow-lg)',
            opacity: '0',
            transform: 'translateY(20px)',
            transition: 'all 0.3s ease-out',
            zIndex: '1000'
        });

        document.body.appendChild(scrollToTopBtn);

        // 显示/隐藏逻辑
        const toggleScrollToTop = () => {
            const scrollTop = window.pageYOffset;
            const shouldShow = scrollTop > 300;
            
            scrollToTopBtn.style.opacity = shouldShow ? '1' : '0';
            scrollToTopBtn.style.transform = shouldShow ? 'translateY(0)' : 'translateY(20px)';
            scrollToTopBtn.style.pointerEvents = shouldShow ? 'auto' : 'none';
        };

        window.addEventListener('scroll', utils.throttle(toggleScrollToTop, 100));

        // 点击事件
        scrollToTopBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        // 初始化图标
        if (window.lucide) {
            lucide.createIcons();
        }
    }

    // 优化卡片切换动画
    optimizeCardTabs() {
        const cardTabs = document.querySelectorAll('.card-tab');
        
        cardTabs.forEach(tab => {
            tab.addEventListener('click', (event) => {
                event.preventDefault();
                
                const targetId = tab.dataset.target;
                const container = tab.closest('.card-body');
                
                if (!container || !targetId) return;
                
                // 移除所有活动状态
                container.querySelectorAll('.card-tab').forEach(t => t.classList.remove('active'));
                container.querySelectorAll('.leaders-list, .fear-greed-container').forEach(c => c.classList.remove('active'));
                
                // 添加活动状态
                tab.classList.add('active');
                const targetElement = container.querySelector(`#${targetId}`);
                if (targetElement) {
                    targetElement.classList.add('active');
                }
                
                // 触觉反馈（如果支持）
                if (navigator.vibrate) {
                    navigator.vibrate(10);
                }
            });
        });
    }

    // 优化工具提示
    optimizeTooltips() {
        const infoButtons = document.querySelectorAll('.info-btn');
        
        infoButtons.forEach(btn => {
            let tooltipTimeout;
            
            const showTooltip = (event) => {
                const tooltip = btn.dataset.tooltip;
                if (!tooltip) return;
                
                clearTimeout(tooltipTimeout);
                
                const tooltipElement = document.getElementById('tooltip');
                if (tooltipElement) {
                    tooltipElement.textContent = tooltip;
                    tooltipElement.classList.add('show');
                    
                    // 定位工具提示
                    const rect = btn.getBoundingClientRect();
                    tooltipElement.style.left = `${rect.left + rect.width / 2}px`;
                    tooltipElement.style.top = `${rect.top - 10}px`;
                    tooltipElement.style.transform = 'translate(-50%, -100%)';
                }
            };
            
            const hideTooltip = () => {
                tooltipTimeout = setTimeout(() => {
                    const tooltipElement = document.getElementById('tooltip');
                    if (tooltipElement) {
                        tooltipElement.classList.remove('show');
                    }
                }, 100);
            };
            
            // 移动端使用点击而不是悬停
            if (utils.isTouchDevice()) {
                btn.addEventListener('click', (event) => {
                    event.stopPropagation();
                    showTooltip(event);
                    
                    // 3秒后自动隐藏
                    setTimeout(hideTooltip, 3000);
                });
                
                // 点击其他地方隐藏
                document.addEventListener('click', hideTooltip);
            } else {
                btn.addEventListener('mouseenter', showTooltip);
                btn.addEventListener('mouseleave', hideTooltip);
            }
        });
    }

    // 优化长列表滚动
    optimizeLongLists() {
        const scrollableElements = document.querySelectorAll('.dividend-stocks');
        
        scrollableElements.forEach(element => {
            // 添加滚动指示器
            const scrollIndicator = document.createElement('div');
            scrollIndicator.className = 'scroll-indicator';
            scrollIndicator.style.cssText = `
                position: absolute;
                right: 0;
                top: 0;
                bottom: 0;
                width: 4px;
                background: var(--border-color);
                border-radius: 2px;
                opacity: 0;
                transition: opacity 0.3s ease-out;
            `;
            
            const scrollThumb = document.createElement('div');
            scrollThumb.style.cssText = `
                width: 100%;
                background: var(--primary-color);
                border-radius: 2px;
                transition: all 0.3s ease-out;
            `;
            
            scrollIndicator.appendChild(scrollThumb);
            element.style.position = 'relative';
            element.appendChild(scrollIndicator);
            
            // 更新滚动指示器
            const updateScrollIndicator = () => {
                const scrollTop = element.scrollTop;
                const scrollHeight = element.scrollHeight;
                const clientHeight = element.clientHeight;
                
                if (scrollHeight <= clientHeight) {
                    scrollIndicator.style.opacity = '0';
                    return;
                }
                
                scrollIndicator.style.opacity = '1';
                
                const thumbHeight = (clientHeight / scrollHeight) * 100;
                const thumbTop = (scrollTop / scrollHeight) * 100;
                
                scrollThumb.style.height = `${thumbHeight}%`;
                scrollThumb.style.transform = `translateY(${thumbTop / thumbHeight * 100}%)`;
            };
            
            element.addEventListener('scroll', utils.throttle(updateScrollIndicator, 16));
            updateScrollIndicator();
        });
    }
}

// 初始化移动端优化
document.addEventListener('DOMContentLoaded', () => {
    window.mobileOptimizer = new MobileOptimizer();
});