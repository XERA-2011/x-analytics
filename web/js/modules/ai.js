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
                        <div class="ai-badge-label" style="display: flex; align-items: center; justify-content: space-between;">
                            <span>AI Global Cycle Score</span>
                            <button class="info-btn" id="info-ai-score" title="算法说明" style="margin-left: 6px; display: inline-flex; align-items: center;"><i data-lucide="help-circle" width="14"></i></button>
                        </div>
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

                    <!-- 右侧：四大核心验证信号 -->
                    <div class="ai-signals-box">
                        <div class="ai-badge-label">四大核心验证信号</div>
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
                <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none; display: flex; justify-content: space-between; align-items: center;">
                    <div class="card-title"><i data-lucide="git-compare" width="16" style="vertical-align: middle;"></i> 中美 AI 产业五维对比 (US vs CN Matrix)</div>
                    <button class="info-btn" id="info-ai-matrix" title="模型说明" style="display: inline-flex; align-items: center;"><i data-lucide="help-circle" width="14"></i></button>
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
                    <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none; display: flex; justify-content: space-between; align-items: center;">
                        <div class="card-title"><i data-lucide="thermometer" width="16" style="vertical-align: middle;"></i> AI 泡沫温度计 (Bubble Risk)</div>
                        <button class="info-btn" id="info-ai-bubble" title="温度计说明" style="display: inline-flex; align-items: center;"><i data-lucide="help-circle" width="14"></i></button>
                    </div>
        `;

        if (bubble_meter) {
            const usBM = bubble_meter.us || {};
            const cnBM = bubble_meter.cn || {};
            const usRisk = typeof usBM.bubble_risk === 'number' ? usBM.bubble_risk.toFixed(1) : (usBM.bubble_risk || 0);
            const cnRisk = typeof cnBM.bubble_risk === 'number' ? cnBM.bubble_risk.toFixed(1) : (cnBM.bubble_risk || 0);
            html += `
                <div class="bubble-thermo-box">
                    <div class="thermo-row">
                        <div class="thermo-title">美国 AI</div>
                        <div class="thermo-sub">产业价值: <strong>${usBM.value_score}</strong> | 泡沫风险: <strong class="text-down">${usRisk}</strong></div>
                        <div class="thermo-bar"><div class="thermo-fill us-fill" style="width: ${usRisk}%;"></div></div>
                        <div class="thermo-tag status-${usBM.status_class}">${usBM.status_text}</div>
                    </div>
                    <div class="thermo-divider"></div>
                    <div class="thermo-row">
                        <div class="thermo-title">中国 AI</div>
                        <div class="thermo-sub">产业价值: <strong>${cnBM.value_score}</strong> | 泡沫风险: <strong class="text-down">${cnRisk}</strong></div>
                        <div class="thermo-bar"><div class="thermo-fill cn-fill" style="width: ${cnRisk}%;"></div></div>
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
                            <span class="flow-step">能源电力</span>➔
                            <span class="flow-step">AI 芯片</span>➔
                            <span class="flow-step">HBM 存储</span>➔
                            <span class="flow-step">基建液冷</span>➔
                            <span class="flow-step">云计算</span>➔
                            <span class="flow-step">Agent 应用</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 4. 四象限 AI 投资时钟 & 历史周期比对 -->
            <div class="ai-middle-grid" style="margin-bottom: 16px;">
                <!-- 左侧：四象限 AI 投资时钟 -->
                <div class="card" style="padding: 16px;">
                    <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none; display: flex; justify-content: space-between; align-items: center;">
                        <div class="card-title"><i data-lucide="clock" width="16" style="vertical-align: middle;"></i> AI 四象限投资时钟</div>
                        <button class="info-btn" id="info-ai-clock" title="时钟说明" style="display: inline-flex; align-items: center;"><i data-lucide="help-circle" width="14"></i></button>
                    </div>
                    <div class="clock-container">
                        <div class="clock-quadrant q-top-left">泡沫期</div>
                        <div class="clock-quadrant q-top-right">硬件与能源爆发期</div>
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
                <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none; display: flex; justify-content: space-between; align-items: center;">
                    <div class="card-title"><i data-lucide="git-commit" width="16" style="vertical-align: middle;"></i> AI 产业链五阶段扩散模型 (Diffusion Lifecycle)</div>
                    <span style="font-size: 11px; background: rgba(59,130,246,0.15); color: #60a5fa; padding: 2px 8px; border-radius: 4px;">2026 演进：具身智能与工业落地验证中</span>
                </div>
                <div class="ai-roadmap">
                    <div class="ai-step active">
                        <div class="ai-step-num">阶段 1</div>
                        <div class="ai-step-name">能源与算力芯片</div>
                        <div class="ai-step-sub">GEV / NVDA / ARM</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step active">
                        <div class="ai-step-num">阶段 2</div>
                        <div class="ai-step-name">存储与先进封装</div>
                        <div class="ai-step-sub">美光 MU / 台积电</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step active">
                        <div class="ai-step-num">阶段 3</div>
                        <div class="ai-step-name">基建与液冷电源</div>
                        <div class="ai-step-sub">SMCI / VRT / DELL</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step">
                        <div class="ai-step-num">阶段 4</div>
                        <div class="ai-step-name">Agent 与具身智能</div>
                        <div class="ai-step-sub">PLTR / 机器人 / SaaS</div>
                    </div>
                    <div class="ai-arrow">➔</div>
                    <div class="ai-step warning">
                        <div class="ai-step-num">阶段 5</div>
                        <div class="ai-step-name">概念炒作 (泡沫)</div>
                        <div class="ai-step-sub">边缘垃圾小票</div>
                    </div>
                </div>
            </div>

            <!-- 6. 7 Layer AI Industry Grid -->
            <div class="card-header" style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                <h3 class="card-title" style="margin-bottom: 0;"><i data-lucide="layers" width="16" style="vertical-align: middle;"></i> AI 产业链 7 层深度拆解 (L0 - L6)</h3>
                <button class="info-btn" id="info-ai-layers" title="拆解说明" style="display: inline-flex; align-items: center;"><i data-lucide="help-circle" width="14"></i></button>
            </div>

            <div class="ai-layers-grid">
        `;

        if (layers && layers.length > 0) {
            layers.forEach(layer => {
                const avgClass = layer.avg_change > 0 ? 'text-up' : layer.avg_change < 0 ? 'text-down' : '';
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
                        const changeClass = changeVal > 0 ? 'text-up' : changeVal < 0 ? 'text-down' : '';
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

        // 绑定各 ? 按钮点击弹窗事件
        this.bindInfoButtons(data);

        if (window.lucide) {
            lucide.createIcons();
        }
    }

    bindInfoButtons(data) {
        const explanations = data.explanations || {};

        // 1. AI Global Cycle Score 说明弹窗
        const scoreBtn = document.getElementById('info-ai-score');
        if (scoreBtn) {
            scoreBtn.onclick = (e) => {
                e.stopPropagation();
                const exp = explanations.cycle_score || {};
                let weightsHtml = '';
                if (exp.weights) {
                    weightsHtml = `
                        <table style="width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 11px;">
                            <thead>
                                <tr style="border-bottom: 1px solid var(--border-color); text-align: left; color: var(--text-secondary);">
                                    <th style="padding: 4px 6px;">层级</th>
                                    <th style="padding: 4px 6px; text-align: center;">权重</th>
                                    <th style="padding: 4px 6px;">代表标的</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${exp.weights.map(w => `
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                                        <td style="padding: 4px 6px; font-weight: 500;">${w.layer}</td>
                                        <td style="padding: 4px 6px; text-align: center; color: var(--color-primary, #3b82f6); font-weight: 600;">${w.weight}</td>
                                        <td style="padding: 4px 6px; color: var(--text-secondary);">${w.targets}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `;
                }
                const bodyHtml = `
                    <div class="ai-info-modal" style="white-space: normal; font-size: 12px; color: var(--text-primary);">
                        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-color); border-radius: 6px; padding: 8px 10px; margin-bottom: 10px;">
                            <div style="font-weight: 600; font-size: 12px; color: var(--color-primary, #3b82f6); margin-bottom: 4px;">🧮 算力加权六因子核心公式</div>
                            <div style="font-family: monospace; font-size: 11px; background: rgba(0,0,0,0.25); padding: 4px 8px; border-radius: 4px; color: #e2e8f0; margin-bottom: 4px; line-height: 1.4;">
                                weighted_pct = L0×15% + L1×30% + L2×20% + L3×15% + L4×10% + L5×10%<br/>
                                heat_score = Min(100, Max(0, 50.0 + weighted_pct × 7.5))
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary);">包含 2026 年核心约束因子：L0 能源电力 (15%) 与 L1-L5 全链条动能。</div>
                        </div>

                        <div style="font-weight: 600; font-size: 12px; margin-bottom: 4px; color: var(--text-secondary);">📊 各层级因子算法权重分配：</div>
                        ${weightsHtml}

                        <div style="background: rgba(255, 255, 255, 0.02); border-left: 3px solid var(--color-primary, #3b82f6); padding: 6px 8px; font-size: 11px; color: var(--text-secondary); margin-top: 8px;">
                            <div><strong>💡 得分区间：</strong>70+ 分能源与算力爆发 | 50~70 分稳健消化 | &lt;40 分周期回调</div>
                            <div style="margin-top: 2px; color: var(--text-muted, #94a3b8);">⚡ 数据抓取：直连美股与A股盘中数据，后台每 10 分钟自动预热更新。</div>
                        </div>
                    </div>
                `;
                utils.showInfoModal(exp.title || 'AI Global Cycle Score 算法说明', bodyHtml);
            };
        }

        // 2. 中美 AI 5D 对比弹窗
        const matrixBtn = document.getElementById('info-ai-matrix');
        if (matrixBtn) {
            matrixBtn.onclick = (e) => {
                e.stopPropagation();
                const exp = explanations.us_cn_matrix || {};
                let dimsHtml = '';
                if (exp.dimensions) {
                    dimsHtml = exp.dimensions.map(d => `
                        <div style="background: rgba(255,255,255,0.03); padding: 6px 8px; border-radius: 4px; border-left: 3px solid #3b82f6;">
                            <div style="font-weight: 600; color: var(--text-primary); display: flex; justify-content: space-between; font-size: 12px;">
                                <span>${d.name}</span>
                                <span style="color: var(--text-secondary); font-size: 11px;">(满分 ${d.max} 分)</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px; line-height: 1.3;">${d.desc}</div>
                        </div>
                    `).join('');
                }
                const bodyHtml = `
                    <div class="ai-info-modal" style="white-space: normal; font-size: 12px; color: var(--text-primary);">
                        <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 8px;">
                            从 5 大核心维度综合量化评估中美 AI 产业竞争力与阶段偏离：
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 6px;">
                            ${dimsHtml}
                        </div>
                    </div>
                `;
                utils.showInfoModal(exp.title || '中美 AI 产业五维对比模型评定标准', bodyHtml);
            };
        }

        // 3. AI 泡沫温度计弹窗
        const bubbleBtn = document.getElementById('info-ai-bubble');
        if (bubbleBtn) {
            bubbleBtn.onclick = (e) => {
                e.stopPropagation();
                const exp = explanations.bubble_meter || {};
                const bodyHtml = `
                    <div class="ai-info-modal" style="white-space: normal; font-size: 12px; color: var(--text-primary); line-height: 1.4;">
                        <div style="background: rgba(255,255,255,0.03); border-radius: 4px; padding: 8px 10px; margin-bottom: 8px;">
                            <div style="font-weight: 600; color: var(--color-primary, #3b82f6); margin-bottom: 2px;">🌡️ 双维度剥离判定法则</div>
                            <div style="color: var(--text-secondary); font-size: 11px;">
                                系统将“产业真实价值分”与“二级市场估值泡沫风险分”分离计算：
                            </div>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 6px; font-size: 11px;">
                            <div style="padding: 6px 8px; background: rgba(34, 197, 94, 0.1); border-radius: 4px; color: #4ade80;">
                                ✅ <strong>健康资本扩张期：</strong> 芯片需求爆满 + 云巨头 CapEx 资本开支激增，股价有强劲业绩支撑。
                            </div>
                            <div style="padding: 6px 8px; background: rgba(239, 68, 68, 0.1); border-radius: 4px; color: #f87171;">
                                ⚠️ <strong>泡沫风险预警期：</strong> 算力龙头滞涨，资金转向无业绩的边缘垃圾题材暴涨，估值情绪过热。
                            </div>
                        </div>
                    </div>
                `;
                utils.showInfoModal(exp.title || 'AI 泡沫温度计说明', bodyHtml);
            };
        }

        // 4. AI 投资时钟弹窗
        const clockBtn = document.getElementById('info-ai-clock');
        if (clockBtn) {
            clockBtn.onclick = (e) => {
                e.stopPropagation();
                const exp = explanations.investment_clock || {};
                const bodyHtml = `
                    <div class="ai-info-modal" style="white-space: normal; font-size: 12px; color: var(--text-primary); line-height: 1.4;">
                        <div style="background: rgba(255,255,255,0.03); border-radius: 4px; padding: 8px 10px; margin-bottom: 8px;">
                            <div style="font-weight: 600; color: var(--color-primary, #3b82f6); margin-bottom: 2px;">🕒 四象限轮动与历史基准比对</div>
                            <div style="color: var(--text-secondary); font-size: 11px;">
                                借鉴美林时钟原理，将 AI 周期划分为【硬件爆发期 ➔ 需求验证期 ➔ 应用爆发期 ➔ 泡沫破裂期】。
                            </div>
                        </div>
                        <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4; background: rgba(255,255,255,0.02); padding: 8px 10px; border-radius: 4px;">
                            📌 <strong>历史参考映射：</strong> 当前 AI 处于类似 1997 年 Dot-Com 互联网大建设初期（卖路由器/服务器的基础设施盈利阶段），尚未演变为 2000 年全民炒作带.com垃圾小票的末期泡沫破裂阶段。
                        </div>
                    </div>
                `;
                utils.showInfoModal(exp.title || 'AI 四象限投资时钟说明', bodyHtml);
            };
        }

        // 5. 产业链 7 层拆解说明弹窗
        const layersBtn = document.getElementById('info-ai-layers');
        if (layersBtn) {
            layersBtn.onclick = (e) => {
                e.stopPropagation();
                const bodyHtml = `
                    <div class="ai-info-modal" style="white-space: normal; font-size: 12px; color: var(--text-primary);">
                        <div style="font-weight: 600; font-size: 12px; margin-bottom: 6px; color: var(--text-primary);">AI 产业链 7 层结构与传导逻辑 (L0 - L6)：</div>
                        <div style="display: flex; flex-direction: column; gap: 5px; font-size: 11px;">
                            <div style="padding: 5px 8px; background: rgba(255,255,255,0.03); border-radius: 4px;">
                                <strong style="color: var(--color-primary, #3b82f6);">L0 能源电力基建</strong>：GEV (电气)、CEG (核电)、VST 及 ETN，2026 AI 瓶颈红利。
                            </div>
                            <div style="padding: 5px 8px; background: rgba(255,255,255,0.03); border-radius: 4px;">
                                <strong style="color: var(--color-primary, #3b82f6);">L1 算力芯片与架构</strong>：包含 NVDA, AMD, AVGO, ARM, MRVL 及费半 ETF，资本最核心风向标。
                            </div>
                            <div style="padding: 5px 8px; background: rgba(255,255,255,0.03); border-radius: 4px;">
                                <strong style="color: var(--color-primary, #3b82f6);">L2 存储与代工</strong>：美光 HBM 内存与台积电 CoWoS 封装，体现真实硬件产能供需。
                            </div>
                            <div style="padding: 5px 8px; background: rgba(255,255,255,0.03); border-radius: 4px;">
                                <strong style="color: var(--color-primary, #3b82f6);">L3 数据中心基建</strong>：服务器与液冷/电源（SMCI / VRT / DELL），反映基建落地开支。
                            </div>
                            <div style="padding: 5px 8px; background: rgba(255,255,255,0.03); border-radius: 4px;">
                                <strong style="color: var(--color-primary, #3b82f6);">L4 云计算四大巨头</strong>：微软/谷歌/亚马逊/Meta/甲骨文，其 AI 资本开支是全产业链上限。
                            </div>
                            <div style="padding: 5px 8px; background: rgba(255,255,255,0.03); border-radius: 4px;">
                                <strong style="color: var(--color-primary, #3b82f6);">L5 Agent 与应用</strong>：Palantir、ServiceNow、Salesforce 等 SaaS 软件，体现商业化变现成果。
                            </div>
                            <div style="padding: 5px 8px; background: rgba(255,255,255,0.03); border-radius: 4px;">
                                <strong style="color: #ef4444;">L6 A股/边缘概念</strong>：寒武纪/海光等龙头与游资偏好题材，狂热暴涨预示短线情绪近尾声。
                            </div>
                        </div>
                    </div>
                `;
                utils.showInfoModal('AI 产业链 7 层深度拆解说明', bodyHtml);
            };
        }
    }
}

