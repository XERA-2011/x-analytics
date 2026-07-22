class AIMarketController {
    constructor() {
    }

    async loadData() {
        console.log('🤖 加载 AI 产业链数据...');
        try {
            const data = await api.getAIOverview();
            this.renderOverview(data);
        } catch (error) {
            console.error('加载 AI 产业链数据失败:', error);
            utils.renderError('ai-container', 'AI 产业链数据加载失败');
        }
    }

    renderOverview(data) {
        const container = document.getElementById('ai-container');
        if (!container) return;

        if (data.error) {
            utils.renderError('ai-container', data.error);
            return;
        }

        const { heat_score, cycle_phase, cycle_status, cycle_desc, signals, layers } = data;

        // 渲染顶部：AI 仪表盘 & 周期分析
        const scoreClass = heat_score >= 70 ? 'text-up' : heat_score <= 40 ? 'text-down' : 'text-neutral';
        
        let html = `
            <!-- 顶部 AI 热度仪表盘 & 周期指示器 -->
            <div class="card hero ai-hero-card" style="margin-bottom: 16px;">
                <div class="ai-header-grid">
                    <!-- 左侧：热度得分 -->
                    <div class="ai-score-box">
                        <div class="ai-badge-label">AI 产业综合火热度</div>
                        <div class="ai-score-num ${scoreClass}">${heat_score} <span class="ai-score-max">/ 100</span></div>
                        <div class="ai-score-tip">基于算力/存储/巨头CapEx/软件加权推算</div>
                    </div>

                    <!-- 中间：产业周期判定 -->
                    <div class="ai-cycle-box">
                        <div class="ai-badge-label">当前产业周期阶段</div>
                        <div class="ai-cycle-title status-${cycle_status}">${cycle_phase}</div>
                        <div class="ai-cycle-desc">${cycle_desc}</div>
                    </div>

                    <!-- 右侧：三大关键监控信号 -->
                    <div class="ai-signals-box">
                        <div class="ai-badge-label">三大核心验证信号</div>
                        <div class="ai-signals-list">
        `;

        if (signals && signals.length > 0) {
            signals.forEach(sig => {
                const tagClass = sig.status_class === 'up' ? 'heat-red' : 'heat-green';
                html += `
                    <div class="ai-signal-item">
                        <div class="ai-signal-head">
                            <span class="ai-signal-title">${sig.title}</span>
                            <span class="heat-tag ${tagClass}">${sig.status}</span>
                        </div>
                        <div class="ai-signal-sub">${sig.desc}</div>
                    </div>
                `;
            });
        }

        html += `
                        </div>
                    </div>
                </div>
            </div>

            <!-- 资金轮动与扩散路径 Roadmap -->
            <div class="card" style="margin-bottom: 16px; padding: 16px;">
                <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none;">
                    <div class="card-title"><i data-lucide="git-commit" width="16" style="vertical-align: middle;"></i> AI 产业链资金扩散路径 (Capital Rotation Lifecycle)</div>
                </div>
                <div class="ai-roadmap">
                    <div class="ai-step active">
                        <div class="ai-step-num">1</div>
                        <div class="ai-step-name">算力芯片</div>
                        <div class="ai-step-sub">NVDA / AMD</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step active">
                        <div class="ai-step-num">2</div>
                        <div class="ai-step-name">存储 HBM</div>
                        <div class="ai-step-sub">美光 MU</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step active">
                        <div class="ai-step-num">3</div>
                        <div class="ai-step-name">基建与电源</div>
                        <div class="ai-step-sub">SMCI / VRT</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step">
                        <div class="ai-step-num">4</div>
                        <div class="ai-step-name">应用与 Agent</div>
                        <div class="ai-step-sub">PLTR / SaaS</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step warning">
                        <div class="ai-step-num">5</div>
                        <div class="ai-step-name">概念炒作 (泡沫)</div>
                        <div class="ai-step-sub">边缘垃圾小票</div>
                    </div>
                </div>
            </div>

            <!-- 6 Layer AI Industry Grid -->
            <div class="card-header" style="margin-bottom: 12px;">
                <h3 class="card-title"><i data-lucide="layers" width="16" style="vertical-align: middle;"></i> AI 产业链 6 层深度拆解</h3>
            </div>

            <div class="ai-layers-grid">
        `;

        if (layers && layers.length > 0) {
            layers.forEach(layer => {
                const avgClass = layer.avg_change > 0 ? 'text-up-us' : layer.avg_change < 0 ? 'text-down-us' : '';
                const avgSign = layer.avg_change > 0 ? '+' : '';
                
                html += `
                    <div class="card ai-layer-card">
                        <div class="ai-layer-header">
                            <div>
                                <span class="ai-layer-id">${layer.layer_id}</span>
                                <span class="ai-layer-star">${layer.star}</span>
                                <div class="ai-layer-title">${layer.title}</div>
                            </div>
                            <div class="ai-layer-avg ${avgClass}">${avgSign}${layer.avg_change}%</div>
                        </div>
                        
                        <div class="ai-layer-importance">${layer.importance}</div>
                        <div class="ai-layer-desc">${layer.desc}</div>

                        <div class="ai-layer-items">
                `;

                if (layer.items && layer.items.length > 0) {
                    layer.items.forEach(item => {
                        const changeVal = item.change_pct || 0.0;
                        const isCN = item.is_sector || layer.layer_id === 'L6';
                        const upClass = isCN ? 'text-up' : 'text-up-us';
                        const downClass = isCN ? 'text-down' : 'text-down-us';
                        const changeClass = changeVal > 0 ? upClass : changeVal < 0 ? downClass : '';
                        const sign = changeVal > 0 ? '+' : '';
                        const priceHtml = (item.is_sector || !item.price) ? '' : `<span class="ai-item-price">$${item.price.toFixed(2)}</span>`;

                        html += `
                            <div class="ai-item-row">
                                <div class="ai-item-info">
                                    <span class="ai-item-name">${item.name}</span>
                                    <span class="ai-item-code">${item.symbol || ''}</span>
                                </div>
                                <div class="ai-item-price-box">
                                    ${priceHtml}
                                    <span class="ai-item-change ${changeClass}">${sign}${changeVal.toFixed(2)}%</span>
                                </div>
                            </div>
                        `;
                    });
                }

                html += `
                        </div>
                    </div>
                `;
            });
        }

        html += `</div>`;

        container.innerHTML = html;
        container.classList.remove('loading');

        if (window.lucide) {
            lucide.createIcons();
        }
    }
}
