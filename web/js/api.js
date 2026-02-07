// API 调用模块

class API {
    constructor() {
        this.baseURL = '/analytics';
        this.timeout = 15000; // 增加到15秒超时
        this.activeRequests = new Map(); // 跟踪活跃请求
        this.cache = new Map(); // 前端缓存
        this.cacheTTL = 60000; // 缓存有效期 60秒
    }

    // 通用请求方法
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const method = options.method || 'GET';
        const requestKey = `${method}:${endpoint}`;

        // 1. 检查缓存 (仅针对 GET 请求)
        if (method === 'GET') {
            const cached = this.cache.get(requestKey);
            if (cached) {
                const now = Date.now();
                if (now - cached.timestamp < this.cacheTTL) {
                    console.debug(`[Cache] Hit: ${endpoint}`);
                    return cached.data;
                } else {
                    this.cache.delete(requestKey); // 过期删除
                }
            }
        }

        // 2. 如果相同的请求正在进行，等待它完成
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

            // 3. 写入缓存 (仅针对 GET 请求且成功响应)
            if (method === 'GET') {
                this.cache.set(requestKey, {
                    timestamp: Date.now(),
                    data: result
                });
            }

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

            const json = await response.json();

            // 处理标准化响应格式
            return this.unwrapResponse(json);
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

    /**
     * 解包标准化 API 响应
     * @param {Object} response - API 响应 {status, data, message, cached_at, ttl}
     * @returns {Object} 解包后的数据或带有 _warming_up/_error 标记的对象
     */
    unwrapResponse(response) {
        // 兼容旧格式 (没有 status 字段)
        if (!response.status) {
            // 检查是否是旧格式的 warming_up
            if (response.error === 'warming_up' || response._warming_up) {
                return {
                    _warming_up: true,
                    message: response.message || '数据预热中'
                };
            }
            // 检查是否是旧格式的错误
            if (response.error) {
                return {
                    _error: true,
                    error: response.error,
                    message: response.message || response.error
                };
            }
            // 旧格式正常数据，直接返回
            return response;
        }

        // 新标准化格式
        switch (response.status) {
            case 'ok':
                // 返回数据，附加元信息
                const data = response.data || {};
                if (typeof data === 'object') {
                    data._cached_at = response.cached_at;
                    data._ttl = response.ttl;
                    if (response.message) {
                        data._stale = true;
                    }
                }
                return data;

            case 'warming_up':
                return {
                    _warming_up: true,
                    error: 'warming_up',
                    message: response.message || '数据预热中，请稍后刷新'
                };

            case 'error':
                return {
                    _error: true,
                    error: response.message || '数据获取失败',
                    message: response.message,
                    data: response.data
                };

            default:
                console.warn(`未知的响应状态: ${response.status}`);
                return response.data || response;
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

    // 香港市场 API
    async getHKIndices() {
        return this.request('/market-hk/indices');
    }

    async getHKFearGreed() {
        return this.request('/market-hk/fear-greed');
    }

    async getCNIndices() {
        return this.request('/market-cn/indices');
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

    async getGoldFearGreed() {
        return this.request('/metals/fear-greed');
    }

    async getSilverFearGreed() {
        return this.request('/metals/silver-fear-greed');
    }

    async getMetalSpotPrices() {
        return this.request('/metals/spot-prices');
    }

    // 超买超卖信号 API
    async getCNOverboughtOversold(period = 'daily') {
        return this.request(`/market-cn/signals/overbought-oversold?period=${period}`);
    }

    async getUSOverboughtOversold(period = 'daily') {
        return this.request(`/market-us/signals/overbought-oversold?period=${period}`);
    }

    async getHKOverboughtOversold(period = 'daily') {
        return this.request(`/market-hk/signals/overbought-oversold?period=${period}`);
    }

    async getGoldOverboughtOversold(period = 'daily') {
        return this.request(`/metals/gold/signals/overbought-oversold?period=${period}`);
    }

    async getSilverOverboughtOversold(period = 'daily') {
        return this.request(`/metals/silver/signals/overbought-oversold?period=${period}`);
    }

    // 宏观数据 API
    async getLPR() {
        return this.request('/market-cn/lpr');
    }

    // 基金 API


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