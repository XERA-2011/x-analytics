// 工具函数模块

class Utils {
    // 格式化数字
    static formatNumber(value, precision = 2) {
        if (value === null || value === undefined || isNaN(value)) {
            return '--';
        }

        const num = parseFloat(value);

        if (Math.abs(num) >= 1e8) {
            return `${(num / 1e8).toFixed(precision)}亿`;
        } else if (Math.abs(num) >= 1e4) {
            return `${(num / 1e4).toFixed(precision)}万`;
        } else {
            return num.toFixed(precision);
        }
    }

    // 格式化百分比
    static formatPercentage(value, precision = 2) {
        if (value === null || value === undefined || isNaN(value)) {
            return '--';
        }

        const num = parseFloat(value);
        const formatted = num.toFixed(precision);
        return `${formatted}%`;
    }

    // 格式化价格变化 (支持不同市场颜色: us=绿涨红跌, cn/metals=红涨绿跌)
    static formatChange(value, precision = 2, market = 'cn') {
        if (value === null || value === undefined || isNaN(value)) {
            return { text: '--', class: '' };
        }

        const num = parseFloat(value);
        const formatted = num.toFixed(precision);
        const text = num > 0 ? `+${formatted}%` : `${formatted}%`;

        // 根据市场确定颜色方案
        let className = '';
        if (market === 'us') {
            // 美国市场: 绿涨红跌
            className = num > 0 ? 'text-up-us' : num < 0 ? 'text-down-us' : '';
        } else {
            // 中国市场/金属: 红涨绿跌
            className = num > 0 ? 'text-up' : num < 0 ? 'text-down' : '';
        }

        return { text, class: className };
    }

    // 格式化时间
    static formatTime(timestamp) {
        if (!timestamp) return '--';

        try {
            const date = new Date(timestamp);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (error) {
            return timestamp;
        }
    }

    // 格式化日期 (For Footer)
    static formatDate(timestamp) {
        return this.formatTime(timestamp);
    }

    // 格式化相对时间
    static formatRelativeTime(timestamp) {
        if (!timestamp) return '--';

        try {
            const now = new Date();
            const date = new Date(timestamp);
            const diff = now - date;
            const seconds = Math.floor(diff / 1000);
            const minutes = Math.floor(seconds / 60);
            const hours = Math.floor(minutes / 60);
            const days = Math.floor(hours / 24);

            if (days > 0) return `${days}天前`;
            if (hours > 0) return `${hours}小时前`;
            if (minutes > 0) return `${minutes}分钟前`;
            return '刚刚';
        } catch (error) {
            return timestamp;
        }
    }

    // Fear & Greed Score Class
    static getScoreClass(score) {
        if (score >= 75) return 'extreme-greed';
        if (score >= 55) return 'greed';
        if (score <= 25) return 'extreme-fear';
        if (score <= 45) return 'fear';
        return 'neutral';
    }

    // Overbought/Oversold signal class (uses backend levels when available)
    static getOboClass(data) {
        if (!data) return 'obo-neutral';
        const levels = Array.isArray(data.levels) ? data.levels.slice() : null;
        const strength = typeof data.strength === 'number' ? data.strength : 50;

        if (levels && levels.length > 0) {
            levels.sort((a, b) => b.min - a.min);
            const matched = levels.find(l => strength >= l.min);
            const signal = matched ? matched.signal : (data.signal || 'neutral');
            if (signal === 'overbought') return 'obo-overbought';
            if (signal === 'oversold') return 'obo-oversold';
            return 'obo-neutral';
        }

        if (data.signal === 'overbought') return 'obo-overbought';
        if (data.signal === 'oversold') return 'obo-oversold';
        return 'obo-neutral';
    }

    /**
     * Render overbought/oversold signal into a container.
     * Shared across all market controllers (CN, US, HK, Metals).
     * @param {string} containerId - Target DOM element ID
     * @param {Object} data - Signal data from API
     */
    static renderOverboughtOversold(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (data.error || data._warming_up) {
            container.innerHTML = `<div class="obo-loading">信号计算中...</div>`;
            return;
        }

        const signalClass = Utils.getOboClass(data);
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

    static getFearGreedMetaLine(data) {
        const meta = data?.meta || {};
        const parts = [];

        if (meta.methodology === 'custom_proxy') {
            parts.push('口径: 自定义 Proxy');
        } else if (meta.methodology === 'technical_composite') {
            parts.push('口径: 技术合成');
        }
        if (meta.factor_framework === 'normalized_v1') {
            parts.push('统一因子归一化');
        }

        const updateTime = data?.update_time || data?._cached_at;
        if (updateTime) {
            parts.push(`更新时间: ${Utils.formatTime(updateTime)}`);
        }

        if (meta.reference_note) {
            parts.push(meta.reference_note);
        } else if (meta.comparable_scope === 'same_market_only') {
            parts.push('仅适合同市场内观察');
        }

        return parts.join(' · ');
    }

    static getFearGreedComparableNote(data) {
        const meta = data?.meta || {};
        const lines = [];

        if (meta.factor_framework === 'normalized_v1') {
            lines.push('统一框架：当前指数已接入统一因子归一化框架。');
        }

        if (meta.comparable_scope === 'same_market_only') {
            lines.push('可比性：更适合同一市场内部纵向观察，不建议直接跨市场横向比较。');
        }

        if (meta.reference_note) {
            lines.push(`补充说明：${meta.reference_note}`);
        }

        return lines.join('\n');
    }

    static buildFearGreedModalBody(data) {
        const sections = [];
        if (data?.explanation) sections.push(data.explanation);

        const note = Utils.getFearGreedComparableNote(data);
        if (note) sections.push(note);

        return sections.join('\n\n');
    }

    // Gold/Silver Ratio Color
    static getRatioColor(ratio) {
        if (!ratio) return 'var(--text-primary)';
        // 80+ is high (Silver cheap) -> Good for Silver
        if (ratio > 85) return 'var(--accent-green)';
        // 60- is low (Gold cheap) -> Good for Gold
        if (ratio < 65) return 'var(--accent-red)';
        return 'var(--text-primary)';
    }

    // 防抖函数
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // 节流函数
    static throttle(func, limit) {
        let inThrottle;
        return function (...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // 安全的JSON解析
    static safeJSONParse(str, defaultValue = null) {
        try {
            return JSON.parse(str);
        } catch (error) {
            console.warn('JSON解析失败:', error);
            return defaultValue;
        }
    }

    // 生成随机ID
    static generateId(prefix = 'id') {
        return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    // 检查是否为移动设备
    static isMobile() {
        return window.innerWidth <= 768;
    }

    // 检查是否为触摸设备
    static isTouchDevice() {
        return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    }

    // 复制到剪贴板
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (error) {
            console.error('复制失败:', error);
            return false;
        }
    }



    // 获取URL参数
    static getUrlParam(name) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    }

    // 设置URL参数
    static setUrlParam(name, value) {
        const url = new URL(window.location);
        url.searchParams.set(name, value);
        window.history.replaceState({}, '', url);
    }

    // 本地存储封装
    static storage = {
        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (error) {
                console.error('存储失败:', error);
                return false;
            }
        },

        get(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (error) {
                console.error('读取存储失败:', error);
                return defaultValue;
            }
        },

        remove(key) {
            try {
                localStorage.removeItem(key);
                return true;
            } catch (error) {
                console.error('删除存储失败:', error);
                return false;
            }
        },

        clear() {
            try {
                localStorage.clear();
                return true;
            } catch (error) {
                console.error('清空存储失败:', error);
                return false;
            }
        }
    };

    // Error Rendering
    static renderError(containerId, message) {
        const container = document.getElementById(containerId);
        if (container) {
            // Convert warming_up to user-friendly message
            let displayMessage = message;
            let icon = 'alert-circle';
            if (message === 'warming_up' || message === 'warming up') {
                displayMessage = '数据预热中，请稍后刷新';
                icon = 'clock';
            }
            container.innerHTML = `<div class="loading error"><i data-lucide="${icon}" width="16"></i> ${displayMessage}</div>`;
            if (window.lucide) lucide.createIcons();
            // Clear any existing warming up timer
            Utils.clearWarmingUpTimer(containerId);
        }
    }

    /**
     * Render warming up state with automatic timeout
     * Per project standards: warming_up state max 60 seconds, then convert to error
     * @param {string} containerId - Container element ID
     * @param {number} timeoutMs - Timeout in milliseconds (default 60000)
     */
    static renderWarmingUp(containerId, timeoutMs = 60000) {
        const container = document.getElementById(containerId);
        if (!container) return;

        // Clear any existing timer first
        Utils.clearWarmingUpTimer(containerId);

        container.innerHTML = `<div class="loading warming-up"><i data-lucide="clock" width="16"></i> 数据预热中，请稍后刷新</div>`;
        if (window.lucide) lucide.createIcons();

        // Store timer ID on container dataset for cleanup
        const timerId = setTimeout(() => {
            // Check if still showing warming-up (not replaced by real data)
            if (container.querySelector('.warming-up')) {
                Utils.renderError(containerId, '数据暂时不可用，请稍后重试');
            }
        }, timeoutMs);

        container.dataset.warmupTimer = timerId;
    }

    /**
     * Clear warming up timer if data loaded successfully
     * @param {string} containerId - Container element ID
     */
    static clearWarmingUpTimer(containerId) {
        const container = document.getElementById(containerId);
        if (container?.dataset?.warmupTimer) {
            clearTimeout(parseInt(container.dataset.warmupTimer));
            delete container.dataset.warmupTimer;
        }
    }

    // Modal
    static showInfoModal(title, content) {
        // Remove existing modal if any
        const existingModal = document.querySelector('.modal-overlay');
        if (existingModal) existingModal.remove();

        const html = `
            <div class="modal-overlay" onclick="if(event.target===this) this.remove()">
                <div class="modal-content">
                    <div class="modal-header">
                        <div class="modal-title">${title}</div>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">
                            <i data-lucide="x" width="20"></i>
                        </button>
                    </div>
                    <div class="modal-body">${content}</div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', html);
        if (window.lucide) lucide.createIcons();
    }

    // Screenshot Share Modal (Minimalist)
    static showShareModal(dataURL, title = '截图分享') {
        const existingModal = document.querySelector('.modal-overlay');
        if (existingModal) existingModal.remove();

        // Minimalist layout matching reference screenshot exactly
        const html = `
            <div class="modal-overlay share-modal-overlay" style="display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(0,0,0,0.85); z-index: 10000;" onclick="if(event.target===this) this.remove()">
                
                <button style="position: absolute; top: 24px; right: 24px; background: rgba(255,255,255,0.1); border: none; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: background 0.2s;" onclick="this.closest('.share-modal-overlay').remove()" onmouseover="this.style.background='rgba(255,255,255,0.2)'" onmouseout="this.style.background='rgba(255,255,255,0.1)'">
                    <i data-lucide="x" width="20"></i>
                </button>
                
                <div style="position: relative; display: flex; justify-content: center; align-items: center; max-width: 90vw;">
                    <img src="${dataURL}" style="max-width: 100%; max-height: 80vh; object-fit: contain; border-radius: 4px; box-shadow: 0 8px 30px rgba(0,0,0,0.5);" />
                    
                    <!-- Floating actions panel mimicking the screenshot exactly -->
                    <div style="position: absolute; bottom: 20px; display: flex; align-items: center; justify-content: center; background: rgba(30, 30, 30, 0.95); backdrop-filter: blur(8px); padding: 4px 16px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
                        
                        <button id="btn-download-img" style="background: transparent; border: none; color: rgba(255,255,255,0.85); font-size: 13px; font-weight: 500; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; padding: 10px 8px; width: 96px; transition: color 0.2s;" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='rgba(255,255,255,0.85)'">
                            <i data-lucide="download" width="16"></i> 下载保存
                        </button>
                        
                        <div style="width: 1px; height: 16px; background: rgba(255,255,255,0.2); margin: 0 16px;"></div>
                        
                        <button id="btn-copy-img" style="background: transparent; border: none; color: rgba(255,255,255,0.85); font-size: 13px; font-weight: 500; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; padding: 10px 8px; width: 96px; transition: color 0.2s;" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='rgba(255,255,255,0.85)'">
                            <i data-lucide="copy" width="16"></i> 复制图片
                        </button>
                        
                    </div>
                </div>
                
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', html);
        if (window.lucide) lucide.createIcons();

        // Bind events
        document.getElementById('btn-download-img').onclick = function() {
            const a = document.createElement('a');
            a.href = dataURL;
            a.download = `${title}_${new Date().toISOString().slice(0, 10)}.png`;
            a.click();

            const btn = this;
            if (btn) {
                const originalHtml = btn.innerHTML;
                btn.innerHTML = `<i data-lucide="check" width="16"></i> 下载成功`;
                if (window.lucide) lucide.createIcons();
                setTimeout(() => {
                    btn.innerHTML = originalHtml;
                    if (window.lucide) lucide.createIcons();
                }, 2000);
            }
        };

        document.getElementById('btn-copy-img').onclick = async function() {
            const btn = this;
            const originalHtml = btn.innerHTML;
            btn.innerHTML = '<i data-lucide="loader" width="16" class="spin"></i> 正在复制';
            try {
                const res = await fetch(dataURL);
                const blob = await res.blob();
                
                if (navigator.clipboard && navigator.clipboard.write) {
                    await navigator.clipboard.write([
                        new ClipboardItem({
                            [blob.type]: blob
                        })
                    ]);
                    
                    btn.innerHTML = '<i data-lucide="check" width="16"></i> 复制成功';
                    if (window.lucide) lucide.createIcons();
                    setTimeout(() => {
                        btn.innerHTML = originalHtml;
                        if (window.lucide) lucide.createIcons();
                    }, 2000);
                } else {
                    btn.innerHTML = originalHtml;
                    if (window.lucide) lucide.createIcons();
                    alert('当前浏览器不支持直接复制图片，请使用下载保存功能');
                }
            } catch (err) {
                console.error('复制失败', err);
                btn.innerHTML = '<i data-lucide="x-circle" width="16"></i> 复制失败';
                if (window.lucide) lucide.createIcons();
                setTimeout(() => {
                    btn.innerHTML = originalHtml;
                    if (window.lucide) lucide.createIcons();
                }, 2000);
            }
        };
    }

    // 颜色工具
    static color = {
        // 根据数值获取颜色
        getChangeColor(value) {
            if (value > 0) return '#10b981'; // 绿色
            if (value < 0) return '#ef4444'; // 红色
            return '#6b7280'; // 灰色
        },

        // 根据百分比获取渐变色
        getGradientColor(percentage, startColor = '#ef4444', endColor = '#10b981') {
            // 简化实现，实际可以使用更复杂的颜色插值
            return percentage > 50 ? endColor : startColor;
        }
    };
}

// 全局工具函数
window.utils = Utils;
