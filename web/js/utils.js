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
            // 美股: 绿涨红跌
            className = num > 0 ? 'text-up-us' : num < 0 ? 'text-down-us' : '';
        } else {
            // 沪港深/金属: 红涨绿跌
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

    // 显示通知
    static showNotification(message, type = 'info', duration = 3000) {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // 添加样式
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 16px',
            borderRadius: '8px',
            color: 'white',
            fontSize: '14px',
            fontWeight: '500',
            zIndex: '9999',
            opacity: '0',
            transform: 'translateX(100%)',
            transition: 'all 0.3s ease-out'
        });

        // 设置背景色
        const colors = {
            info: '#3b82f6',
            success: '#10b981',
            warning: '#f59e0b',
            error: '#ef4444'
        };
        notification.style.backgroundColor = colors[type] || colors.info;

        // 添加到页面
        document.body.appendChild(notification);

        // 显示动画
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 10);

        // 自动移除
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, duration);
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
            container.innerHTML = `<div class="loading error"><i data-lucide="alert-circle" width="16"></i> ${message}</div>`;
            if (window.lucide) lucide.createIcons();
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