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

        if (data._warming_up) {
            console.info('AI 产业周期数据预热中...');
            utils.renderWarmingUp('ai-container');
            this._retryCount = (this._retryCount || 0) + 1;
            if (this._retryCount <= 12 && !this._retryTimer) {
                this._retryTimer = setTimeout(() => {
                    this._retryTimer = null;
                    this.loadData();
                }, 5000);
            }
            return;
        }
        this._retryCount = 0;

        if (data.error || data._error) {
            utils.renderError('ai-container', data.error || data.message || 'AI 产业数据加载失败');
            return;
        }

        const cycleScore = data.cycle_score !== undefined ? data.cycle_score : (data.heat_score || 46.3);
        const { 
            trend_str, risk_level, risk_class, cycle_phase, cycle_status, cycle_desc,
            us_cn_comparison, bubble_meter, rotation_mode, rotation_class, rotation_desc,
            historical_match, signals, layers 
        } = data;

        const scoreClass = cycleScore >= 65 ? 'text-up' : cycleScore <= 45 ? 'text-down' : 'text-neutral';

        // 计算 SVG Gauge 指针角度 (0~100 映射至 -80° ~ +80° 连续弧度区间)
        const clampedScore = Math.max(0, Math.min(100, Number(cycleScore) || 50));
        const gaugeDegree = -80 + (clampedScore / 100) * 160;

        let activeColor = '#10b981';
        let shortStageLabel = '爆发期';

        if (cycle_status === 'active') {
            activeColor = '#10b981';
            shortStageLabel = '爆发期';
        } else if (cycle_status === 'neutral') {
            activeColor = '#3b82f6';
            shortStageLabel = '探索期';
        } else if (cycle_status === 'warning') {
            activeColor = '#ef4444';
            shortStageLabel = '预警期';
        } else if (cycle_status === 'cooling') {
            activeColor = '#64748b';
            shortStageLabel = '降温期';
        }

        const trendTag = trend_str || (cycle_status === 'warning' ? '⚠️ 预警' : cycle_status === 'cooling' ? '↓ 回调' : cycle_status === 'active' ? '↑ 强劲' : '→ 震荡');
        const riskTag = risk_level || (cycle_status === 'warning' || cycle_status === 'cooling' ? '偏高' : '中等');
        const riskCls = risk_class || '';
        const riskClassAttr = (riskCls === 'high' || cycle_status === 'warning' || cycle_status === 'cooling') ? 'style="color: var(--color-danger); border-color: rgba(239, 68, 68, 0.3); background: rgba(239, 68, 68, 0.1);"' : '';

        let html = `
            <!-- 1. AI 全球产业周期总评分 Dashboard Header -->
            <div class="card hero ai-hero-card" style="margin-bottom: 16px;">
                <div class="ai-header-grid">
                    <!-- 左侧：AI Market Heat -->
                    <div class="ai-score-box">
                        <div class="ai-badge-label" style="display: flex; align-items: center; justify-content: space-between;">
                            <span>AI Market Heat（综合热度分）</span>
                            <button class="info-btn" id="info-ai-score" title="算法说明" style="margin-left: 6px; display: inline-flex; align-items: center;"><i data-lucide="help-circle" width="14"></i></button>
                        </div>
                        <div class="ai-score-num ${scoreClass}">${cycleScore} <span class="ai-score-max">/ 100</span></div>
                        <div class="ai-score-scope" style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">
                            平滑七因子模型 (40%即时 + 60%历史滚动均值)
                        </div>
                        <div class="ai-meta-row" style="margin-top: 6px; gap: 6px; display: flex; flex-wrap: wrap;">
                            <span class="ai-trend-tag">${trendTag}</span>
                            <span class="ai-risk-tag" ${riskClassAttr}>风险: ${riskTag}</span>
                            ${data.momentum_1d != null ? `<span class="ai-momentum-tag" style="font-size: 11px; padding: 2px 7px; border-radius: 4px; background: rgba(0,0,0,0.05); color: var(--text-secondary); font-weight: 500;">1D即时: ${data.momentum_1d}分</span>` : ''}
                        </div>
                    </div>

                    <!-- 中间：当前产业周期阶段 (带 SVG 动态仪表盘) -->
                    <div class="ai-cycle-box">
                        <div class="ai-badge-label">当前市场阶段</div>
                        <div class="ai-cycle-content">
                            <div class="ai-gauge-wrapper">
                                <svg viewBox="0 0 160 95" class="ai-cycle-gauge">
                                    <defs>
                                        <linearGradient id="grad-active" x1="0%" y1="0%" x2="100%" y2="100%">
                                            <stop offset="0%" stop-color="#06b6d4" />
                                            <stop offset="100%" stop-color="#10b981" />
                                        </linearGradient>
                                        <linearGradient id="grad-neutral" x1="0%" y1="0%" x2="100%" y2="100%">
                                            <stop offset="0%" stop-color="#3b82f6" />
                                            <stop offset="100%" stop-color="#06b6d4" />
                                        </linearGradient>
                                        <linearGradient id="grad-warning" x1="0%" y1="0%" x2="100%" y2="100%">
                                            <stop offset="0%" stop-color="#f59e0b" />
                                            <stop offset="100%" stop-color="#ef4444" />
                                        </linearGradient>
                                        <linearGradient id="grad-cooling" x1="0%" y1="0%" x2="100%" y2="100%">
                                            <stop offset="0%" stop-color="#64748b" />
                                            <stop offset="100%" stop-color="#94a3b8" />
                                        </linearGradient>
                                        <filter id="gauge-glow" x="-20%" y="-20%" width="140%" height="140%">
                                            <feGaussianBlur stdDeviation="2.5" result="blur" />
                                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                                        </filter>
                                    </defs>

                                    <!-- 底色完整弧线轨迹 -->
                                    <path d="M 15 80 A 65 65 0 0 1 145 80" fill="none" stroke="rgba(226, 232, 240, 0.8)" stroke-width="12" stroke-linecap="round"/>

                                    <!-- 4 阶段不同颜色弧线分段：左(降温/筑底) -> 中左(探索) -> 中右(爆发) -> 右(预警/过热) -->
                                    <path d="M 15 80 A 65 65 0 0 1 34.04 34.04" fill="none" stroke="url(#grad-cooling)" stroke-width="11" stroke-linecap="round"/>
                                    <path d="M 36 32 A 65 65 0 0 1 78 15" fill="none" stroke="url(#grad-neutral)" stroke-width="11" stroke-linecap="round"/>
                                    <path d="M 82 15 A 65 65 0 0 1 124 32" fill="none" stroke="url(#grad-active)" stroke-width="11" stroke-linecap="round"/>
                                    <path d="M 125.96 34.04 A 65 65 0 0 1 145 80" fill="none" stroke="url(#grad-warning)" stroke-width="11" stroke-linecap="round"/>

                                    <!-- 旋转游标针与高亮点 -->
                                    <g class="gauge-needle-group" style="transform: rotate(${gaugeDegree.toFixed(1)}deg); transform-origin: 80px 80px;">
                                        <line x1="80" y1="80" x2="80" y2="24" stroke="var(--text-primary)" stroke-width="3" stroke-linecap="round"/>
                                        <circle cx="80" cy="24" r="5" fill="${activeColor}" filter="url(#gauge-glow)" class="gauge-pulse-dot"/>
                                        <circle cx="80" cy="80" r="5" fill="var(--text-primary)"/>
                                    </g>
                                </svg>
                                <div class="ai-gauge-badge status-${cycle_status}">${shortStageLabel}</div>
                            </div>
                            <div class="ai-cycle-info">
                                <div class="ai-cycle-title status-${cycle_status}">${cycle_phase}</div>
                                <div class="ai-cycle-desc status-${cycle_status}">${cycle_desc}</div>
                            </div>
                        </div>
                    </div>

                    <!-- 右侧：四大核心验证信号 (2x2 微型卡片网格) -->
                    <div class="ai-signals-box">
                        <div class="ai-badge-label" style="display: flex; justify-content: space-between; align-items: center;">
                            <span>四大核心验证信号</span>
                            <span class="signal-status-pulse">● LIVE</span>
                        </div>
                        <div class="ai-signals-grid">
        `;

        if (signals && signals.length > 0) {
            const icons = ['zap', 'cpu', 'database', 'cloud'];
            signals.forEach((sig, idx) => {
                const iconName = icons[idx % icons.length];
                const isUp = sig.status_class === 'up';
                const badgeClass = isUp ? 'up' : 'down';
                const beaconClass = isUp ? 'up' : 'down';

                html += `
                    <div class="ai-signal-card">
                        <div class="ai-signal-card-head">
                            <span class="ai-signal-card-title">
                                <i data-lucide="${iconName}" width="13" style="vertical-align: middle;"></i>
                                ${sig.title.replace(/^信号\d：/, '')}
                            </span>
                            <span class="ai-signal-card-badge ${badgeClass}">
                                <span class="beacon-dot ${beaconClass}"></span>
                                ${sig.status}
                            </span>
                        </div>
                        <div class="ai-signal-card-sub" title="${sig.desc}">${sig.desc}</div>
                    </div>
                `;
            });
        }

        html += `
                        </div>
                    </div>
                </div>
            </div>

            <!-- 2. AI 资金轮动健康度与扩散路径 (Capital Rotation) -->
            <div class="card ai-card-module" style="margin-bottom: 16px;">
                <div class="card-header" style="margin-bottom: 8px;">
                    <div class="card-title">
                        <i data-lucide="refresh-cw" width="16" style="vertical-align: middle;"></i> AI 资金轮动健康度监测 (Capital Rotation)
                    </div>
                    <button class="info-btn" id="info-ai-rotation" title="轮动说明"><i data-lucide="help-circle" width="14"></i></button>
                </div>
                <div class="card-body">
                    <div class="rotation-box">
                        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                            <span class="rotation-badge rotation-${rotation_class}">${rotation_mode || '均衡传导 (扩散中)'}</span>
                            <span style="font-size: 11px; color: var(--text-tertiary);">实时监测 L0~L6 各层动能分化与资金流向</span>
                        </div>
                        <div class="rotation-desc" style="margin-top: 6px;">${rotation_desc || '--'}</div>
                        <div class="rotation-flow" style="margin-top: 10px;">
                            <span class="flow-step" style="background: rgba(16, 185, 129, 0.12); color: #059669; font-weight: 700;">L0 能源电力</span>
                            <span style="color: var(--text-tertiary);">➔</span>
                            <span class="flow-step" style="background: rgba(59, 130, 246, 0.12); color: #2563eb; font-weight: 700;">L1 算力芯片</span>
                            <span style="color: var(--text-tertiary);">➔</span>
                            <span class="flow-step" style="background: rgba(59, 130, 246, 0.08); color: var(--text-primary);">L2 存储代工</span>
                            <span style="color: var(--text-tertiary);">➔</span>
                            <span class="flow-step" style="background: rgba(59, 130, 246, 0.08); color: var(--text-primary);">L3 服务器液冷</span>
                            <span style="color: var(--text-tertiary);">➔</span>
                            <span class="flow-step" style="background: rgba(59, 130, 246, 0.08); color: var(--text-primary);">L4 云计算巨头</span>
                            <span style="color: var(--text-tertiary);">➔</span>
                            <span class="flow-step" style="background: rgba(168, 85, 247, 0.1); color: #9333ea;">L5 软件Agent</span>
                            <span style="color: var(--text-tertiary);">➔</span>
                            <span class="flow-step" style="background: rgba(239, 68, 68, 0.1); color: #dc2626;">L6 边缘概念</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 3. 中美 AI 对比与泡沫风险 (对称双卡片栅格) -->
            <div class="ai-grid-row">
                <!-- 左卡：中美 AI 产业五维对比 -->
                <div class="card ai-card-module">
                    <div class="card-header" style="margin-bottom: 4px;">
                        <div class="card-title" style="font-size: 13px;"><i data-lucide="git-compare" width="15" style="vertical-align: middle;"></i> 中美 AI 产业五维对比 (Radar Matrix)</div>
                        <button class="info-btn" id="info-ai-matrix" title="模型说明"><i data-lucide="help-circle" width="14"></i></button>
                    </div>
                    <div class="card-body" style="padding: 2px 6px 4px 6px; justify-content: center; align-items: center;">
                        ${(() => {
                            if (!us_cn_comparison) return '';
                            const keys = Object.keys(us_cn_comparison);
                            const cx = 150, cy = 82, r = 52;
                            const angles = [-Math.PI / 2, -Math.PI / 2 + (2 * Math.PI / 5), -Math.PI / 2 + (4 * Math.PI / 5), -Math.PI / 2 + (6 * Math.PI / 5), -Math.PI / 2 + (8 * Math.PI / 5)];

                            const labelConfigs = [
                                { anchor: 'middle', baseline: 'auto', dx: 0, dy: -9 },
                                { anchor: 'start', baseline: 'central', dx: 9, dy: 1 },
                                { anchor: 'start', baseline: 'hanging', dx: 4, dy: 14 },
                                { anchor: 'end', baseline: 'hanging', dx: -4, dy: 14 },
                                { anchor: 'end', baseline: 'central', dx: -9, dy: 1 }
                            ];

                            const usPoints = [];
                            const cnPoints = [];
                            const axisLines = [];
                            const gridPolys = [0.33, 0.66, 1.0];
                            const labels = [];

                            keys.forEach((key, idx) => {
                                const item = us_cn_comparison[key];
                                const angle = angles[idx];
                                const usRatio = Math.min(1.0, item.us / item.max);
                                const cnRatio = Math.min(1.0, item.cn / item.max);

                                const usX = cx + r * usRatio * Math.cos(angle);
                                const usY = cy + r * usRatio * Math.sin(angle);
                                usPoints.push(`${usX.toFixed(1)},${usY.toFixed(1)}`);

                                const cnX = cx + r * cnRatio * Math.cos(angle);
                                const cnY = cy + r * cnRatio * Math.sin(angle);
                                cnPoints.push(`${cnX.toFixed(1)},${cnY.toFixed(1)}`);

                                const axX = cx + r * Math.cos(angle);
                                const axY = cy + r * Math.sin(angle);
                                axisLines.push(`<line x1="${cx}" y1="${cy}" x2="${axX.toFixed(1)}" y2="${axY.toFixed(1)}" stroke="rgba(203,213,225,0.6)" stroke-dasharray="2 2"/>`);

                                const cfg = labelConfigs[idx] || { anchor: 'middle', baseline: 'auto', dx: 0, dy: 0 };
                                const lx = axX + cfg.dx;
                                const ly = axY + cfg.dy;
                                labels.push(`<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="${cfg.anchor}" dominant-baseline="${cfg.baseline}" font-size="10" font-weight="600" fill="var(--text-secondary)">${item.label}</text>`);
                            });

                            const webPolysHtml = gridPolys.map(scale => {
                                const pts = angles.map(a => `${(cx + r * scale * Math.cos(a)).toFixed(1)},${(cy + r * scale * Math.sin(a)).toFixed(1)}`).join(' ');
                                return `<polygon points="${pts}" fill="none" stroke="rgba(226,232,240,0.8)" stroke-width="1"/>`;
                            }).join('');

                            return `
                                <div class="svg-radar-layout" style="width: 100%;">
                                    <div class="svg-radar-chart-box" style="max-width: 290px; margin: 0 auto;">
                                        <svg viewBox="0 0 300 168" class="svg-radar-chart" style="max-height: 165px;">
                                            ${webPolysHtml}
                                            ${axisLines.join('')}
                                            <polygon points="${usPoints.join(' ')}" fill="rgba(59,130,246,0.22)" stroke="#3b82f6" stroke-width="1.8" class="radar-poly-us"/>
                                            <polygon points="${cnPoints.join(' ')}" fill="rgba(222,41,16,0.22)" stroke="#de2910" stroke-width="1.8" class="radar-poly-cn"/>
                                            ${labels.join('')}
                                        </svg>
                                        <div class="svg-radar-legend" style="margin-top: 2px; font-size: 11px; gap: 14px;">
                                            <span class="legend-item"><span class="legend-dot-us"></span>美国 AI (优势)</span>
                                            <span class="legend-item"><span class="legend-dot-cn"></span>中国 AI (追赶)</span>
                                        </div>
                                    </div>
                                </div>
                            `;
                        })()}
                    </div>
                </div>

                <!-- 右卡：AI 泡沫温度计 -->
                <div class="card ai-card-module">
                    <div class="card-header" style="margin-bottom: 4px;">
                        <div class="card-title" style="font-size: 13px;"><i data-lucide="thermometer" width="15" style="vertical-align: middle;"></i> AI 泡沫温度计 (Bubble Risk)</div>
                        <button class="info-btn" id="info-ai-bubble" title="温度计说明"><i data-lucide="help-circle" width="14"></i></button>
                    </div>
                    <div class="card-body" style="padding: 2px 6px 4px 6px; justify-content: space-between;">
                        ${(() => {
                            if (!bubble_meter) return '';
                            const usBM = bubble_meter.us || {};
                            const cnBM = bubble_meter.cn || {};
                            const usRisk = typeof usBM.bubble_risk === 'number' ? usBM.bubble_risk.toFixed(1) : (usBM.bubble_risk || 0);
                            const cnRisk = typeof cnBM.bubble_risk === 'number' ? cnBM.bubble_risk.toFixed(1) : (cnBM.bubble_risk || 0);

                            const renderThermoRow = (country, bm, riskVal, isCn) => {
                                const colorGrad = isCn ? 'url(#grad-cn-thermo)' : 'url(#grad-us-thermo)';
                                const badgeClass = bm.status_class === 'healthy' ? 'healthy' : 'warning';
                                const peStr = bm.pe_ratio ? `真实加权 PE: <strong>${bm.pe_ratio}x</strong> (标杆 ${bm.pe_benchmark || '--'}x)` : `产业价值分: <strong>${bm.value_score}</strong>`;

                                return `
                                    <div class="svg-thermo-row" style="background: var(--bg-secondary, #f8fafc); border: 1px solid var(--border-light); border-radius: 6px; padding: 7px 10px; margin-bottom: 5px;">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; flex-wrap: wrap; gap: 4px;">
                                            <span style="font-size: 11.5px; font-weight: 700; color: var(--text-primary);">${country} AI 估值偏离与泡沫风险</span>
                                            <span class="svg-thermo-badge ${badgeClass}" style="font-size: 9.5px; padding: 1px 6px; border-radius: 4px;">${bm.status_text}</span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 10.5px; color: var(--text-secondary); margin-bottom: 4px;">
                                            <span>${peStr}</span>
                                            <span>泡沫风险: <strong class="text-down" style="font-family: var(--font-mono); font-weight: 700;">${riskVal} / 100</strong></span>
                                        </div>
                                        <svg class="svg-thermo-bar-svg" viewBox="0 0 300 12" style="width: 100%; height: 12px; display: block;">
                                            <defs>
                                                <linearGradient id="grad-us-thermo" x1="0%" y1="0%" x2="100%" y2="0%">
                                                    <stop offset="0%" stop-color="#3b82f6" />
                                                    <stop offset="100%" stop-color="#10b981" />
                                                </linearGradient>
                                                <linearGradient id="grad-cn-thermo" x1="0%" y1="0%" x2="100%" y2="0%">
                                                    <stop offset="0%" stop-color="#f59e0b" />
                                                    <stop offset="100%" stop-color="#ef4444" />
                                                </linearGradient>
                                            </defs>
                                            <rect x="0" y="0" width="300" height="12" rx="6" fill="rgba(226,232,240,0.6)"/>
                                            <rect x="0" y="0" width="${Math.min(300, riskVal * 3)}" height="12" rx="6" fill="${colorGrad}" class="thermo-liquid"/>
                                            <line x1="75" y1="0" x2="75" y2="12" stroke="rgba(255,255,255,0.5)" stroke-width="1"/>
                                            <line x1="150" y1="0" x2="150" y2="12" stroke="rgba(255,255,255,0.7)" stroke-width="1.5"/>
                                            <line x1="225" y1="0" x2="225" y2="12" stroke="rgba(255,255,255,0.5)" stroke-width="1"/>
                                        </svg>
                                    </div>
                                `;
                            };

                            return `
                                <div class="svg-thermo-container" style="gap: 2px;">
                                    ${renderThermoRow('美国', usBM, usRisk, false)}
                                    ${renderThermoRow('中国', cnBM, cnRisk, true)}
                                </div>
                                <div style="font-size: 10px; color: var(--text-tertiary); background: rgba(0,0,0,0.02); padding: 4px 8px; border-radius: 4px; text-align: center; border: 1px dashed var(--border-light); margin-top: 2px;">
                                    折现锚定：10Y 美债收益率 ${data.us_10y_yield || 4.25}% · 动态折现中枢
                                </div>
                            `;
                        })()}
                    </div>
                </div>
            </div>

            <!-- 4. 宏观推演与资本开支底座 (Row 2: 对称双卡片栅格) -->
            <div class="ai-grid-row">
                <!-- 左卡：历史科技周期推演映射 (宏观坐标系) -->
                <div class="card ai-card-module">
                    <div class="card-header" style="margin-bottom: 6px;">
                        <div class="card-title" style="font-size: 13.5px;"><i data-lucide="history" width="16" style="vertical-align: middle;"></i> 历史科技周期推演映射</div>
                        <button class="info-btn" id="info-ai-history" title="推演模型说明"><i data-lucide="help-circle" width="14"></i></button>
                    </div>
                    <div class="card-body" style="padding-top: 2px;">
                        ${(() => {
                            const hm = data.historical_match;
                            if (!hm) return '<div class="text-secondary">暂无周期比对数据</div>';
                            return `
                                <div class="history-box">
                                    <div class="history-match-era" style="font-size: 13px; font-weight: 700; color: var(--text-primary);">
                                        ${hm.matched_era || '1997年 互联网大建设中期'}
                                    </div>
                                    <div class="history-sim-bar" style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.03); padding: 5px 8px; border-radius: 4px;">
                                        <span style="font-size: 11px; color: var(--color-primary, #3b82f6); font-weight: 600;">周期相似度: ${hm.similarity_pct || 88.2}%</span>
                                        <span style="font-size: 10.5px; color: #059669; font-weight: 700; background: rgba(16, 185, 129, 0.12); padding: 1px 6px; border-radius: 4px;">${hm.bubble_distance || '基础设施扩张特征明显'}</span>
                                    </div>
                                    <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">
                                        ${hm.summary || '全球云巨头年化 CapEx 与芯片出货持续印证，行情更接近互联网基础设施大扩容红利阶段。'}
                                    </div>
                                    <div style="font-size: 10.5px; color: var(--text-tertiary); background: var(--bg-subtle, #f8fafc); border-left: 3px solid var(--color-primary, #3b82f6); padding: 5px 8px; border-radius: 0 4px 4px 0; line-height: 1.35;">
                                        💡 <strong>历史启示：</strong> 对标 1997 年思科与微软基建大扩容期，资本开支与硬件订单处于兑现高潮，应用层变现与盈利模式仍在加速探索阶段。
                                    </div>
                                </div>
                            `;
                        })()}
                    </div>
                </div>

                <!-- 右卡：全球四大云巨头 CapEx 资本开支晴雨表 (基本面底座) -->
                ${(() => {
                    const capex = data.hyperscaler_capex;
                    if (!capex) return '<div class="card ai-card-module"><div class="card-header"><div class="card-title">CapEx 资本开支</div></div><div class="card-body text-secondary">暂无数据</div></div>';
                    return `
                        <div class="card ai-card-module">
                            <div class="card-header" style="margin-bottom: 6px; flex-wrap: wrap; gap: 6px;">
                                <div class="card-title" style="font-size: 13.5px;">
                                    <i data-lucide="bar-chart-3" width="16" style="vertical-align: middle;"></i> 四大云巨头 CapEx 晴雨表
                                </div>
                                <div style="display: flex; align-items: center; gap: 4px; margin-left: auto;">
                                    <span style="font-size: 10.5px; color: #059669; font-weight: 700; background: rgba(16, 185, 129, 0.12); padding: 1px 6px; border-radius: 4px; white-space: nowrap;">
                                        ${capex.status}
                                    </span>
                                </div>
                            </div>
                            <div class="card-body" style="padding-top: 2px;">
                                <div style="font-size: 11.5px; color: var(--text-secondary); margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 4px;">
                                    <span>全球年化运行率: <strong style="color: var(--color-primary, #3b82f6); font-size: 13px;">$${capex.annual_run_rate_b}B</strong></span>
                                    <span>季度同比增速: <strong style="color: #059669; font-size: 13px;">+${capex.yoy_growth_pct}% YoY</strong></span>
                                </div>
                                <div class="ai-capex-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                                    <div class="ai-capex-item">
                                        <div class="ai-capex-company">微软 (Azure)</div>
                                        <div class="ai-capex-val font-mono">$${capex.msft_quarterly_capex_b}B <span style="font-size: 9.5px; font-weight: 500; color: var(--text-tertiary);">/季</span></div>
                                        <div class="ai-capex-sub">数据中心与算力底座</div>
                                    </div>
                                    <div class="ai-capex-item">
                                        <div class="ai-capex-company">亚马逊 (AWS)</div>
                                        <div class="ai-capex-val font-mono">$${capex.amzn_quarterly_capex_b}B <span style="font-size: 9.5px; font-weight: 500; color: var(--text-tertiary);">/季</span></div>
                                        <div class="ai-capex-sub">全球基建与自研芯片</div>
                                    </div>
                                    <div class="ai-capex-item">
                                        <div class="ai-capex-company">谷歌 (GCP)</div>
                                        <div class="ai-capex-val font-mono">$${capex.googl_quarterly_capex_b}B <span style="font-size: 9.5px; font-weight: 500; color: var(--text-tertiary);">/季</span></div>
                                        <div class="ai-capex-sub">TPU集群与搜索AI化</div>
                                    </div>
                                    <div class="ai-capex-item">
                                        <div class="ai-capex-company">Meta (自建集群)</div>
                                        <div class="ai-capex-val font-mono">$${capex.meta_quarterly_capex_b}B <span style="font-size: 9.5px; font-weight: 500; color: var(--text-tertiary);">/季</span></div>
                                        <div class="ai-capex-sub">Llama训练算力基座</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                })()}
            </div>

            <!-- 6. AI 产业链 7 层全景精简拆解 (L0 - L6 代表成分股) -->
            <div class="card ai-card-module" style="margin-bottom: 16px;">
                <div class="card-header" style="margin-bottom: 4px; flex-wrap: wrap; gap: 6px;">
                    <div class="card-title" style="font-size: 13.5px;">
                        <i data-lucide="layers" width="16" style="vertical-align: middle;"></i> AI 产业链 7 层全景拆解 (L0 - L6 代表成分股)
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px; margin-left: auto;">
                        <span style="font-size: 10.5px; color: var(--text-tertiary); white-space: nowrap;">7 大层级 · 30 只核心标的</span>
                        <button class="info-btn" id="info-ai-layers" title="拆解说明"><i data-lucide="help-circle" width="14"></i></button>
                    </div>
                </div>
                <div class="card-body" style="padding: 0 4px 4px 4px;">
                    <div class="ai-layers-stream">
                        ${(() => {
                            if (!layers || layers.length === 0) return '<div class="text-secondary" style="padding: 12px;">暂无产业链数据</div>';
                            return layers.map(layer => {
                                const avgVal = layer.avg_change || 0.0;
                                const isAvgUp = avgVal > 0;
                                const avgClass = isAvgUp ? 'avg-up' : avgVal < 0 ? 'avg-down' : '';
                                const avgSign = isAvgUp ? '+' : '';

                                let stocksHtml = '';
                                if (layer.items && layer.items.length > 0) {
                                    stocksHtml = layer.items.map(item => {
                                        const changeVal = item.change_pct;
                                        const isCnStock = layer.layer_id === 'L6';
                                        const isUp = changeVal > 0;
                                        const chipClass = changeVal != null ? (isUp ? 'chip-up' : changeVal < 0 ? 'chip-down' : 'chip-neutral') : 'chip-neutral';
                                        const sign = isUp ? '+' : '';
                                        const changeStr = changeVal != null ? `${sign}${changeVal.toFixed(2)}%` : '--';
                                        const currency = isCnStock ? '¥' : '$';
                                        const priceStr = item.price != null ? `${currency}${item.price.toFixed(2)}` : '--';
                                        const peStr = item.pe != null && item.pe > 0 ? `PE: ${item.pe.toFixed(1)}x` : '';
                                        const mcapStr = item.market_cap != null && item.market_cap > 0 ? (isCnStock ? `市值: ${item.market_cap.toFixed(0)}亿` : `市值: $${(item.market_cap / 1000).toFixed(1)}B`) : '';

                                        // 提取精简且辨识度高的标的名称
                                        const cleanName = item.symbol === 'SMH' ? 'SMH半导体' :
                                            item.name
                                                .replace(/科技|架构|ASIC|AI服务器|液冷电源|核电|电力|电气|电脑|云/g, '')
                                                .trim() || item.name;

                                        // 悬浮 Tooltip 呈现机构级完整信息
                                        const tooltip = `${item.name} (${item.symbol})\n最新价: ${priceStr}  涨跌幅: ${changeStr}${peStr ? '\n' + peStr : ''}${mcapStr ? '\n' + mcapStr : ''}`;

                                        return `
                                            <span class="ai-stock-chip ${chipClass}" title="${tooltip}">
                                                <span class="ai-stock-chip-name">${cleanName}</span>
                                                <span class="ai-stock-chip-chg font-mono">${changeStr}</span>
                                            </span>
                                        `;
                                    }).join('');
                                }

                                const cleanTitle = layer.title.replace(/^.{2}：/, '');

                                return `
                                    <div class="ai-stream-row">
                                        <div class="ai-stream-header">
                                            <div class="ai-stream-meta">
                                                <span class="ai-stream-badge font-mono">${layer.layer_id}</span>
                                                <span class="ai-stream-title">${cleanTitle}</span>
                                                <span class="ai-stream-tag">${layer.importance}</span>
                                            </div>
                                            <div class="ai-stream-avg">
                                                <span class="ai-stream-avg-val ${avgClass}">${avgSign}${avgVal.toFixed(2)}%</span>
                                            </div>
                                        </div>
                                        <div class="ai-stream-stocks">
                                            ${stocksHtml}
                                        </div>
                                    </div>
                                `;
                            }).join('');
                        })()}
                    </div>
                </div>
            </div>
        `;

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
                const defaultWeights = [
                    { layer: 'L0 能源电力', weight: '10%', targets: 'GEV, CEG, VST, ETN' },
                    { layer: 'L1 算力芯片', weight: '25%', targets: 'NVDA, AMD, AVGO, ARM, MRVL' },
                    { layer: 'L2 存储代工', weight: '20%', targets: 'MU, TSM, ASML' },
                    { layer: 'L3 服务器与液冷基建', weight: '15%', targets: 'SMCI, DELL, VRT' },
                    { layer: 'L4 云计算四大巨头', weight: '10%', targets: 'MSFT, GOOGL, AMZN, META, ORCL' },
                    { layer: 'L5 软件应用', weight: '10%', targets: 'PLTR, NOW, CRM' },
                    { layer: 'L6 A股AI龙头', weight: '10%', targets: '寒武纪, 海光, 旭创, 工业富联, 浪潮信息' }
                ];
                const weightsList = (exp.weights && exp.weights.length > 0) ? exp.weights : defaultWeights;

                const weightsHtml = `
                    <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-color); border-radius: 6px; padding: 6px 8px; margin: 8px 0;">
                        <div style="font-weight: 600; font-size: 11.5px; margin-bottom: 6px; color: var(--text-primary); display: flex; align-items: center; gap: 4px;">
                            <span>📊</span> 各层级因子算法权重分配
                        </div>
                        <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                            <thead>
                                <tr style="border-bottom: 1px solid var(--border-color); text-align: left; color: var(--text-secondary);">
                                    <th style="padding: 4px 6px; font-weight: 600;">层级</th>
                                    <th style="padding: 4px 6px; text-align: center; font-weight: 600;">权重</th>
                                    <th style="padding: 4px 6px; font-weight: 600;">代表标的</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${weightsList.map(w => `
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                                        <td style="padding: 4px 6px; font-weight: 500; white-space: nowrap;">${w.layer}</td>
                                        <td style="padding: 4px 6px; text-align: center; color: var(--color-primary, #3b82f6); font-weight: 700;">${w.weight}</td>
                                        <td style="padding: 4px 6px; color: var(--text-secondary); word-break: break-word;">${w.targets}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;

                const bodyHtml = `
                    <div class="ai-info-modal" style="white-space: normal; font-size: 12px; color: var(--text-primary);">
                        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-color); border-radius: 6px; padding: 8px 10px; margin-bottom: 8px;">
                            <div style="font-weight: 600; font-size: 12px; color: var(--color-primary, #3b82f6); margin-bottom: 4px;">🧮 平滑七因子双轨算法公式</div>
                            <div style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 10.5px; background: rgba(0,0,0,0.3); padding: 6px 8px; border-radius: 4px; color: #e2e8f0; margin-bottom: 6px; line-height: 1.45; word-break: break-word;">
                                <div><span style="color:#93c5fd;">weighted_pct_raw</span> = L0×10% + L1×25% + L2×20% + L3×15% + L4×10% + L5×10% + L6×10%</div>
                                <div style="margin-top: 2px;"><span style="color:#fcd34d;">momentum_1d</span> = Min(100, Max(0, 50.0 + weighted_pct_raw × 7.5))</div>
                                <div style="margin-top: 2px;"><span style="color:#86efac;">cycle_score (平滑热度)</span> = 40% × 当期即时动能 + 60% × 历史滚动均值</div>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">双轨模型：同时提供敏感反映今日盘中的【1D 即时动能】与过滤短线噪音的【平滑综合热度分】。</div>
                        </div>

                        ${weightsHtml}

                        <div style="background: rgba(255, 255, 255, 0.02); border-left: 3px solid var(--color-primary, #3b82f6); border-radius: 0 4px 4px 0; padding: 6px 10px; font-size: 11px; color: var(--text-secondary); margin-top: 8px; line-height: 1.45;">
                            <div><strong>💡 得分区间：</strong><span style="color: #4ade80;">70+</span> 爆发 | <span style="color: #38bdf8;">50~70</span> 稳健 | <span style="color: #f87171;">&lt;40</span> 回调</div>
                            <div style="margin-top: 3px; color: var(--text-muted, #94a3b8); font-size: 10.5px;">⚡ 数据抓取：直连美股与A股盘中实时行情，后台每 10 分钟自动更新。</div>
                        </div>
                    </div>
                `;
                utils.showInfoModal(exp.title || 'AI 市场热度分（平滑七因子模型）', bodyHtml);
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
                            从 5 大核心维度综合量化评估中美 AI 产业竞争力（融合实时动能、动态估值与财报基准）：
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
                                ✅ <strong>健康资本扩张期：</strong> 芯片需求饱满 + 云巨头 CapEx 资本开支激增，股价有强劲业绩支撑。
                            </div>
                            <div style="padding: 6px 8px; background: rgba(239, 68, 68, 0.1); border-radius: 4px; color: #f87171;">
                                ⚠️ <strong>泡沫风险预警期：</strong> 算力龙头滞涨，资金转向无业绩的边缘题材炒作，估值情绪过热。
                            </div>
                        </div>
                    </div>
                `;
                utils.showInfoModal(exp.title || 'AI 泡沫温度计说明', bodyHtml);
            };
        }

        // 3.5 AI 资金轮动监测说明弹窗
        const rotationBtn = document.getElementById('info-ai-rotation');
        if (rotationBtn) {
            rotationBtn.onclick = (e) => {
                e.stopPropagation();
                const exp = explanations.rotation || {};
                const bodyHtml = `
                    <div class="ai-info-modal" style="white-space: normal; font-size: 12px; color: var(--text-primary); line-height: 1.5;">
                        <div style="background: var(--bg-tertiary, rgba(0,0,0,0.03)); border-radius: 6px; padding: 10px 12px; margin-bottom: 10px;">
                            <div style="font-weight: 600; color: var(--color-primary, #3b82f6); margin-bottom: 4px;">🔄 资金轮动监测与动态判定原则</div>
                            <div style="color: var(--text-secondary); font-size: 12px;">
                                基于 L0 (能源电力)、L1 (算力芯片)、L5 (应用) 和 L6 (边缘题材) 的盘中实时动能对比动态推演。
                            </div>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 8px; font-size: 12px;">
                            <div style="padding: 8px 12px; border-radius: 6px; display: flex; align-items: flex-start; gap: 6px; font-size: 12px;" class="rotation-badge rotation-healthy">
                                <span style="font-weight: 600; white-space: nowrap;">健康轮动：</span>
                                <span>资金优先集中于电力基础设施 (L0) 与算力芯片 (L1)，硬件及能源动能强劲。</span>
                            </div>
                            <div style="padding: 8px 12px; border-radius: 6px; display: flex; align-items: flex-start; gap: 6px; font-size: 12px;" class="rotation-badge rotation-bubble">
                                <span style="font-weight: 600; white-space: nowrap;">泡沫轮动：</span>
                                <span>边缘小票 (L6) 狂热暴涨，而龙头芯片与能源停滞，警惕概念炒作近尾声。</span>
                            </div>
                            <div style="padding: 8px 12px; border-radius: 6px; display: flex; align-items: flex-start; gap: 6px; font-size: 12px;" class="rotation-badge rotation-neutral">
                                <span style="font-weight: 600; white-space: nowrap;">均衡传导：</span>
                                <span>资金沿“能源 ➔ 芯片 ➔ 存储 ➔ 液冷 ➔ 云计算 ➔ Agent 应用”平稳扩散。</span>
                            </div>
                        </div>
                    </div>
                `;
                utils.showInfoModal(exp.title || 'AI 资金轮动监测说明', bodyHtml);
            };
        }

        // 4. 产业链 7 层拆解说明弹窗
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

        if (window.lucide) {
            lucide.createIcons();
        }
    }
}
