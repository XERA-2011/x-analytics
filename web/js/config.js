/**
 * X-Analytics 全局系统配置
 *
 * 涨跌配色模式配置项 (colorMode)：
 * - 'red-up-green-down': 红涨绿跌 (中国 A 股 / 港股 / 亚洲标准惯例，默认)
 * - 'green-up-red-down': 绿涨红跌 (欧美 / 国际市场惯例)
 * 
 * 修改此配置项可立即全局生效，统一控制当前项目所有 Tab（Global、AI、Gold、QDII）的涨跌视觉呈现。
 */
const APP_CONFIG = {
    // 全局涨跌配色模式配置项 (如需切换为绿涨红跌，直接修改此处为 'green-up-red-down')
    colorMode: 'red-up-green-down',

    // 调色板定义
    palettes: {
        'red-up-green-down': {
            up: '#ef4444',            // 涨：红 (Tailwind Red 500)
            upDark: '#dc2626',        // 涨文字强调深红 (Tailwind Red 600)
            upLight: 'rgba(239, 68, 68, 0.12)', // 浅底色
            upBorder: 'rgba(239, 68, 68, 0.25)', // 边框
            down: '#22c55e',          // 跌：绿 (Tailwind Green 500)
            downDark: '#16a34a',      // 跌文字强调深绿 (Tailwind Green 600)
            downLight: 'rgba(34, 197, 94, 0.12)',
            downBorder: 'rgba(34, 197, 94, 0.25)',
            flat: '#737373'           // 平：灰
        },
        'green-up-red-down': {
            up: '#22c55e',            // 涨：绿 (Tailwind Green 500)
            upDark: '#16a34a',        // 涨文字强调深绿 (Tailwind Green 600)
            upLight: 'rgba(34, 197, 94, 0.12)',
            upBorder: 'rgba(34, 197, 94, 0.25)',
            down: '#ef4444',          // 跌：红 (Tailwind Red 500)
            downDark: '#dc2626',      // 跌文字强调深红 (Tailwind Red 600)
            downLight: 'rgba(239, 68, 68, 0.12)',
            downBorder: 'rgba(239, 68, 68, 0.25)',
            flat: '#737373'           // 平：灰
        }
    },

    // 获取当前配置下的调色板
    getColors() {
        return this.palettes[this.colorMode] || this.palettes['red-up-green-down'];
    },

    // 根据数值获取涨跌 CSS 样式类名 ('text-up' | 'text-down' | '')
    getChangeClass(value) {
        if (value === null || value === undefined || isNaN(value)) return '';
        const num = parseFloat(value);
        if (num > 0) return 'text-up';
        if (num < 0) return 'text-down';
        return '';
    },

    // 根据数值获取对应的十六进制颜色
    getChangeColor(value) {
        const colors = this.getColors();
        if (value === null || value === undefined || isNaN(value)) return colors.flat;
        const num = parseFloat(value);
        if (num > 0) return colors.up;
        if (num < 0) return colors.down;
        return colors.flat;
    },

    // 动态注入并同步 CSS 根变量
    applyThemeColors() {
        const colors = this.getColors();
        const root = document.documentElement;
        if (!root) return;

        root.style.setProperty('--color-up', colors.up);
        root.style.setProperty('--color-up-dark', colors.upDark);
        root.style.setProperty('--color-up-light', colors.upLight);
        root.style.setProperty('--color-up-border', colors.upBorder);

        root.style.setProperty('--color-down', colors.down);
        root.style.setProperty('--color-down-dark', colors.downDark);
        root.style.setProperty('--color-down-light', colors.downLight);
        root.style.setProperty('--color-down-border', colors.downBorder);

        root.style.setProperty('--color-flat', colors.flat);

        // 设置 data-color-mode 属性供 CSS 选择器做深色模式或特化定制
        root.setAttribute('data-color-mode', this.colorMode);
    }
};

// 页面加载前即刻初始化应用 CSS 变量，确保无样式跳变
APP_CONFIG.applyThemeColors();
