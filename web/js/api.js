// API 调用模块

class API {
    constructor() {
        this.baseURL = '/analytics';
        this.timeout = 15000; // 增加到15秒超时
        this.activeRequests = new Map(); // 跟踪活跃请求
    }

    // 通用请求方法
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const requestKey = `${options.method || 'GET'}:${endpoint}`;

        // 如果相同的请求正在进行，等待它完成
        if (this.activeRequests.has(requestKey)) {
            try {
                return await this.activeRequests.get(requestKey);
            } catch (error) {
                // 如果之前的请求失败了，继续执行新请求
            }
        }

        const config = {
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        const requestPromise = this._executeRequest(url, config, endpoint);
        this.activeRequests.set(requestKey, requestPromise);

        try {
            const result = await requestPromise;
            return result;
        } finally {
            this.activeRequests.delete(requestKey);
        }
    }

    async _executeRequest(url, config, endpoint) {
        let controller;
        let timeoutId;

        try {
            controller = new AbortController();
            timeoutId = setTimeout(() => {
                console.log(`请求超时，正在中止: ${endpoint}`);
                controller.abort();
            }, this.timeout);

            const response = await fetch(url, {
                ...config,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            if (timeoutId) clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                console.warn(`请求被中止 [${endpoint}]: 可能是超时或重复请求`);
                throw new Error(`请求超时: ${endpoint}`);
            }

            console.error(`API请求失败 [${endpoint}]:`, error);
            throw error;
        }
    }

    // 取消所有活跃请求
    cancelAllRequests() {
        this.activeRequests.clear();
    }

    // 中国市场 API
    async getCNFearGreed(symbol = 'sh000001', days = 14) {
        return this.request(`/market-cn/fear-greed?symbol=${symbol}&days=${days}`);
    }

    async getCNTopGainers(limit = 10) {
        return this.request(`/market-cn/leaders/gainers?limit=${limit}`);
    }

    async getCNTopLosers(limit = 10) {
        return this.request(`/market-cn/leaders/losers?limit=${limit}`);
    }

    async getCNSectorLeaders() {
        return this.request('/market-cn/leaders/sectors');
    }

    async getCNMarketHeat() {
        return this.request('/market-cn/heat');
    }

    async getCNDividendStocks(limit = 20) {
        return this.request(`/market-cn/dividend/stocks?limit=${limit}`);
    }

    async getCNDividendETFs() {
        return this.request('/market-cn/dividend/etfs');
    }

    async getCNTreasuryYields() {
        return this.request('/market-cn/bonds/treasury');
    }

    async getCNBondAnalysis() {
        return this.request('/market-cn/bonds/analysis');
    }

    // 美国市场 API
    async getUSFearGreed() {
        return this.request('/market-us/fear-greed');
    }

    async getUSCustomFearGreed() {
        return this.request('/market-us/fear-greed/custom');
    }

    async getUSMarketLeaders() {
        return this.request('/market-us/leaders');
    }

    async getUSMarketHeat() {
        return this.request('/market-us/market-heat');
    }

    async getUSBondYields() {
        return this.request('/market-us/bond-yields');
    }

    // Metals
    async getGoldSilverRatio() {
        return this.request('/metals/gold-silver-ratio');
    }

    async getMetalSpotPrices() {
        return this.request('/metals/spot-prices');
    }

    // 宏观数据 API
    async getLPR() {
        return this.request('/market-cn/lpr');
    }

    async getNorthFunds() {
        return this.request('/macro/north-funds');
    }

    async getETFFlow(limit = 10) {
        return this.request(`/macro/etf-flow?limit=${limit}`);
    }

    async getEconomicCalendar(date = null) {
        const params = date ? `?date=${date}` : '';
        return this.request(`/macro/calendar${params}`);
    }

    async triggerWarmup() {
        return this.request('/api/cache/warmup', { method: 'POST' });
    }

    async clearCache() {
        return this.request('/api/cache/clear', { method: 'DELETE' });
    }
}

// 创建全局API实例
window.api = new API();