class AIMarketController {
    constructor() {
    }

    async loadData() {
        console.log('🤖 加载 AI 产业周期终端数据...');
        try {
            const data = await api.getAIOverview();
            this.renderOverview(data);
        } catch (error) {
            console.error('加载 AI 产业周期数据失败:', error);
            utils.renderError('ai-container', 'AI 产业周期终端数据加载失败');
        }
    }

    renderOverview(data) {
        const container = document.getElementById('ai-container');
        if (!container) return;

        if (data.error) {
            utils.renderError('ai-container', data.error);
            return;
        }

        const { 
            heat_score, trend_str, risk_level, cycle_phase, cycle_status, cycle_desc,
            us_cn_comparison, bubble_meter, rotation_mode, rotation_class, rotation_desc,
            historical_match, investment_clock, signals, layers 
        } = data;

        const scoreClass = heat_score >= 70 ? 'text-up' : heat_score <= 40 ? 'text-down' : 'text-neutral';

        let html = `
            <!-- 1. AI 全球产业周期总评分 Dashboard Header -->
            <div class="card hero ai-hero-card" style="margin-bottom: 16px;">
                <div class="ai-header-grid">
                    <!-- 左侧：AI Global Cycle Score -->
                    <div class="ai-score-box">
                        <div class="ai-badge-label">AI Global Cycle Score</div>
                        <div class="ai-score-num ${scoreClass}">${heat_score} <span class="ai-score-max">/ 100</span></div>
                        <div class="ai-meta-row">
                            <span class="ai-trend-tag">${trend_str || '↑ 稳定'}</span>
                            <span class="ai-risk-tag">风险: ${risk_level || '中等'}</span>
                        </div>
                    </div>

                    <!-- 中间：当前产业周期阶段 -->
                    <div class="ai-cycle-box">
                        <div class="ai-badge-label">当前产业周期阶段</div>
                        <div class="ai-cycle-title status-${cycle_status}">${cycle_phase}</div>
                        <div class="ai-cycle-desc">${cycle_desc}</div>
                    </div>

                    <!-- 右侧：三大核心验证信号 -->
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

            <!-- 2. 中美 AI 产业五维对比 (US vs CN 5D Matrix) -->
            <div class="card" style="margin-bottom: 16px; padding: 16px;">
                <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none;">
                    <div class="card-title"><i data-lucide="git-compare" width="16" style="vertical-align: middle;"></i> 中美 AI 产业五维对比 (US vs CN Matrix)</div>
                </div>
                <div class="ai-matrix-grid">
        `;

        if (us_cn_comparison) {
            Object.keys(us_cn_comparison).forEach(key => {
                const item = us_cn_comparison[key];
                const usPct = Math.round((item.us / item.max) * 100);
                const cnPct = Math.round((item.cn / item.max) * 100);

                html += `
                    <div class="ai-matrix-item">
                        <div class="ai-matrix-head">
                            <span class="ai-matrix-label">${item.label}</span>
                            <span class="ai-matrix-vals"><span class="val-us">美 ${item.us}</span> vs <span class="val-cn">中 ${item.cn}</span> (满分${item.max})</span>
                        </div>
                        <div class="ai-matrix-bars">
                            <div class="ai-bar-wrap">
                                <span class="bar-tag">US</span>
                                <div class="bar-outer"><div class="bar-inner us-bg" style="width: ${usPct}%;"></div></div>
                            </div>
                            <div class="ai-bar-wrap">
                                <span class="bar-tag">CN</span>
                                <div class="bar-outer"><div class="bar-inner cn-bg" style="width: ${cnPct}%;"></div></div>
                            </div>
                        </div>
                    </div>
                `;
            });
        }

        html += `
                </div>
            </div>

            <!-- 3. AI 泡沫温度计 & 资金健康轮动 (Bubble Thermometer & Rotation) -->
            <div class="ai-middle-grid" style="margin-bottom: 16px;">
                <!-- 左侧：泡沫温度计 -->
                <div class="card" style="padding: 16px;">
                    <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none;">
                        <div class="card-title"><i data-lucide="thermometer" width="16" style="vertical-align: middle;"></i> AI 泡沫温度计 (Bubble Risk)</div>
                    </div>
        `;

        if (bubble_meter) {
            const usBM = bubble_meter.us || {};
            const cnBM = bubble_meter.cn || {};
            html += `
                <div class="bubble-thermo-box">
                    <div class="thermo-row">
                        <div class="thermo-title">美国 AI</div>
                        <div class="thermo-sub">产业价值: <strong>${usBM.value_score}</strong> | 泡沫风险: <strong class="text-down">${usBM.bubble_risk}</strong></div>
                        <div class="thermo-bar"><div class="thermo-fill us-fill" style="width: ${usBM.bubble_risk}%;"></div></div>
                        <div class="thermo-tag status-${usBM.status_class}">${usBM.status_text}</div>
                    </div>
                    <div class="thermo-divider"></div>
                    <div class="thermo-row">
                        <div class="thermo-title">中国 AI</div>
                        <div class="thermo-sub">产业价值: <strong>${cnBM.value_score}</strong> | 泡沫风险: <strong class="text-down">${cnBM.bubble_risk}</strong></div>
                        <div class="thermo-bar"><div class="thermo-fill cn-fill" style="width: ${cnBM.bubble_risk}%;"></div></div>
                        <div class="thermo-tag status-${cnBM.status_class}">${cnBM.status_text}</div>
                    </div>
                </div>
            `;
        }

        html += `
                </div>

                <!-- 右侧：资金轮动监测 -->
                <div class="card" style="padding: 16px;">
                    <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none;">
                        <div class="card-title"><i data-lucide="repeat" width="16" style="vertical-align: middle;"></i> AI 资金轮动监测</div>
                    </div>
                    <div class="rotation-box">
                        <div class="rotation-badge rotation-${rotation_class}">${rotation_mode}</div>
                        <div class="rotation-desc">${rotation_desc}</div>
                        <div class="rotation-flow">
                            <span class="flow-step">AI 芯片</span>➔
                            <span class="flow-step">HBM 存储</span>➔
                            <span class="flow-step">基建电源</span>➔
                            <span class="flow-step">云计算</span>➔
                            <span class="flow-step">应用 Agent</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 4. 四象限 AI 投资时钟 & 历史周期比对 -->
            <div class="ai-middle-grid" style="margin-bottom: 16px;">
                <!-- 左侧：四象限 AI 投资时钟 -->
                <div class="card" style="padding: 16px;">
                    <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none;">
                        <div class="card-title"><i data-lucide="clock" width="16" style="vertical-align: middle;"></i> AI 四象限投资时钟</div>
                    </div>
                    <div class="clock-container">
                        <div class="clock-quadrant q-top-left">泡沫期</div>
                        <div class="clock-quadrant q-top-right">硬件爆发期</div>
                        <div class="clock-quadrant q-bottom-left">需求验证期</div>
                        <div class="clock-quadrant q-bottom-right">应用爆发期</div>
                        
                        <!-- 坐标打点 -->
                        <div class="clock-dot us-dot" style="left: ${investment_clock?.us_position?.x || 68}%; top: ${100 - (investment_clock?.us_position?.y || 82)}%;">
                            <span class="dot-pin"></span>
                            <span class="dot-label">美国 (${investment_clock?.us_position?.stage})</span>
                        </div>
                        <div class="clock-dot cn-dot" style="left: ${investment_clock?.cn_position?.x || 48}%; top: ${100 - (investment_clock?.cn_position?.y || 62)}%;">
                            <span class="dot-pin"></span>
                            <span class="dot-label">中国 (${investment_clock?.cn_position?.stage})</span>
                        </div>
                    </div>
                </div>

                <!-- 右侧：AI 历史周期比对 -->
                <div class="card" style="padding: 16px;">
                    <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none;">
                        <div class="card-title"><i data-lucide="history" width="16" style="vertical-align: middle;"></i> 历史科技周期推演映射</div>
                    </div>
        `;

        if (historical_match) {
            html += `
                <div class="history-box">
                    <div class="history-match-era">${historical_match.matched_era}</div>
                    <div class="history-sim-bar">
                        <span>周期相似度: <strong>${historical_match.similarity_pct}%</strong></span>
                        <span>${historical_match.bubble_distance}</span>
                    </div>
                    <div class="history-summary">${historical_match.summary}</div>
                </div>
            `;
        }

        html += `
                </div>
            </div>

            <!-- 5. 产业链五阶段扩散 Roadmap -->
            <div class="card" style="margin-bottom: 16px; padding: 16px;">
                <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none;">
                    <div class="card-title"><i data-lucide="git-commit" width="16" style="vertical-align: middle;"></i> AI 产业链五阶段扩散模型 (Diffusion Lifecycle)</div>
                </div>
                <div class="ai-roadmap">
                    <div class="ai-step active">
                        <div class="ai-step-num">阶段 1</div>
                        <div class="ai-step-name">算力芯片</div>
                        <div class="ai-step-sub">NVDA / AMD</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step active">
                        <div class="ai-step-num">阶段 2</div>
                        <div class="ai-step-name">存储 HBM</div>
                        <div class="ai-step-sub">美光 MU</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step active">
                        <div class="ai-step-num">阶段 3</div>
                        <div class="ai-step-name">基建与电源</div>
                        <div class="ai-step-sub">SMCI / VRT</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step">
                        <div class="ai-step-num">阶段 4</div>
                        <div class="ai-step-name">应用与 Agent</div>
                        <div class="ai-step-sub">PLTR / SaaS</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step warning">
                        <div class="ai-step-num">阶段 5</div>
                        <div class="ai-step-name">概念炒作 (泡沫)</div>
                        <div class="ai-step-sub">边缘垃圾小票</div>
                    </div>
                </div>
            </div>

            <!-- 6. 6 Layer AI Industry Grid -->
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
