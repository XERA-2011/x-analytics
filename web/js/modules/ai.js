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

        // 计算 SVG Gauge 指针角度与主题色
        let gaugeDegree = -22.5;
        let activeColor = '#3b82f6';
        let shortStageLabel = '探索期';

        if (cycle_status === 'active') {
            gaugeDegree = -67.5;
            activeColor = '#10b981';
            shortStageLabel = '爆发期';
        } else if (cycle_status === 'neutral') {
            gaugeDegree = -22.5;
            activeColor = '#3b82f6';
            shortStageLabel = '探索期';
        } else if (cycle_status === 'warning') {
            gaugeDegree = 22.5;
            activeColor = '#ef4444';
            shortStageLabel = '预警期';
        } else if (cycle_status === 'cooling') {
            gaugeDegree = 67.5;
            activeColor = '#64748b';
            shortStageLabel = '降温期';
        }

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

                    <!-- 中间：当前产业周期阶段 (带 SVG 动态仪表盘) -->
                    <div class="ai-cycle-box">
                        <div class="ai-badge-label">当前产业周期阶段</div>
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

                                    <!-- 4 阶段不同颜色弧线分段 -->
                                    <path d="M 15 80 A 65 65 0 0 1 34.04 34.04" fill="none" stroke="url(#grad-active)" stroke-width="11" stroke-linecap="round"/>
                                    <path d="M 36 32 A 65 65 0 0 1 78 15" fill="none" stroke="url(#grad-neutral)" stroke-width="11" stroke-linecap="round"/>
                                    <path d="M 82 15 A 65 65 0 0 1 124 32" fill="none" stroke="url(#grad-warning)" stroke-width="11" stroke-linecap="round"/>
                                    <path d="M 125.96 34.04 A 65 65 0 0 1 145 80" fill="none" stroke="url(#grad-cooling)" stroke-width="11" stroke-linecap="round"/>

                                    <!-- 旋转游标针与高亮点 -->
                                    <g class="gauge-needle-group" style="transform: rotate(${gaugeDegree}deg); transform-origin: 80px 80px;">
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

            <!-- 2. 中美 AI 产业五维对比 (SVG 动态雷达图) -->
            <div class="card" style="margin-bottom: 16px; padding: 16px;">
                <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none; display: flex; justify-content: space-between; align-items: center;">
                    <div class="card-title"><i data-lucide="git-compare" width="16" style="vertical-align: middle;"></i> 中美 AI 产业五维对比 (US vs CN Radar Matrix)</div>
                    <button class="info-btn" id="info-ai-matrix" title="模型说明" style="display: inline-flex; align-items: center;"><i data-lucide="help-circle" width="14"></i></button>
                </div>
                ${(() => {
                    if (!us_cn_comparison) return '';
                    const keys = Object.keys(us_cn_comparison);
                    const cx = 180, cy = 135, r = 98;
                    const angles = [-Math.PI / 2, -Math.PI / 2 + (2 * Math.PI / 5), -Math.PI / 2 + (4 * Math.PI / 5), -Math.PI / 2 + (6 * Math.PI / 5), -Math.PI / 2 + (8 * Math.PI / 5)];

                    const usPoints = [];
                    const cnPoints = [];
                    const axisLines = [];
                    const gridPolys = [0.25, 0.5, 0.75, 1.0];
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
                        axisLines.push(`<line x1="${cx}" y1="${cy}" x2="${axX.toFixed(1)}" y2="${axY.toFixed(1)}" stroke="rgba(203,213,225,0.6)" stroke-dasharray="3 3"/>`);

                        const lx = cx + (r + 22) * Math.cos(angle);
                        const ly = cy + (r + 14) * Math.sin(angle);
                        labels.push(`<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="middle" font-size="11" font-weight="600" fill="var(--text-secondary)">${item.label}</text>`);
                    });

                    const webPolysHtml = gridPolys.map(scale => {
                        const pts = angles.map(a => `${(cx + r * scale * Math.cos(a)).toFixed(1)},${(cy + r * scale * Math.sin(a)).toFixed(1)}`).join(' ');
                        return `<polygon points="${pts}" fill="none" stroke="rgba(226,232,240,0.8)" stroke-width="1"/>`;
                    }).join('');

                    return `
                        <div class="svg-radar-layout">
                            <div class="svg-radar-chart-box">
                                <svg viewBox="0 0 360 280" class="svg-radar-chart">
                                    ${webPolysHtml}
                                    ${axisLines.join('')}
                                    <polygon points="${usPoints.join(' ')}" fill="rgba(59,130,246,0.25)" stroke="#3b82f6" stroke-width="2" class="radar-poly-us"/>
                                    <polygon points="${cnPoints.join(' ')}" fill="rgba(239,68,68,0.25)" stroke="#ef4444" stroke-width="2" class="radar-poly-cn"/>
                                    ${labels.join('')}
                                </svg>
                                <div class="svg-radar-legend">
                                    <span class="legend-item"><span class="legend-dot-us"></span>美国 AI (优势覆盖)</span>
                                    <span class="legend-item"><span class="legend-dot-cn"></span>中国 AI (追赶扩展)</span>
                                </div>
                            </div>
                            <div class="ai-matrix-grid" style="grid-template-columns: 1fr;">
                                ${keys.map(key => {
                                    const item = us_cn_comparison[key];
                                    const usPct = Math.round((item.us / item.max) * 100);
                                    const cnPct = Math.round((item.cn / item.max) * 100);
                                    return `
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
                                }).join('')}
                            </div>
                        </div>
                    `;
                })()}
            </div>

            <!-- 3. AI 泡沫温度计 & 资金健康轮动 (Bubble Thermometer & Rotation) -->
            <div class="ai-middle-grid" style="margin-bottom: 16px;">
                <!-- 左侧：SVG 熔炉刻度泡沫温度计 -->
                <div class="card" style="padding: 16px;">
                    <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none; display: flex; justify-content: space-between; align-items: center;">
                        <div class="card-title"><i data-lucide="thermometer" width="16" style="vertical-align: middle;"></i> AI 泡沫温度计 (Bubble Risk)</div>
                        <button class="info-btn" id="info-ai-bubble" title="温度计说明" style="display: inline-flex; align-items: center;"><i data-lucide="help-circle" width="14"></i></button>
                    </div>
                    ${(() => {
                        if (!bubble_meter) return '';
                        const usBM = bubble_meter.us || {};
                        const cnBM = bubble_meter.cn || {};
                        const usRisk = typeof usBM.bubble_risk === 'number' ? usBM.bubble_risk.toFixed(1) : (usBM.bubble_risk || 0);
                        const cnRisk = typeof cnBM.bubble_risk === 'number' ? cnBM.bubble_risk.toFixed(1) : (cnBM.bubble_risk || 0);

                        const renderThermoRow = (country, bm, riskVal, isCn) => {
                            const colorGrad = isCn ? 'url(#grad-cn-thermo)' : 'url(#grad-us-thermo)';
                            const badgeClass = bm.status_class === 'healthy' ? 'healthy' : 'warning';
                            const isHot = Number(riskVal) > 70;
                            const liquidW = Math.min(300, Math.max(0, riskVal * 3));
                            const endX = Math.min(292, Math.max(12, liquidW - 8));
                            const bubbleBubble = isHot ? `<circle cx="${endX}" cy="12" r="3.5" fill="#ef4444" class="bubble-anim"/>` : '';

                            return `
                                <div class="svg-thermo-row">
                                    <div class="svg-thermo-head">
                                        <span class="svg-thermo-title">${country} AI 泡沫偏离风险</span>
                                        <span class="svg-thermo-badge ${badgeClass}">${bm.status_text}</span>
                                    </div>
                                    <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
                                        产业价值分: <strong>${bm.value_score}</strong> | 泡沫风险指数: <strong class="text-down">${riskVal} / 100</strong>
                                    </div>
                                    <svg class="svg-thermo-bar-svg" viewBox="0 0 300 24">
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
                                        <rect x="0" y="4" width="300" height="16" rx="8" fill="rgba(226,232,240,0.6)"/>
                                        <rect x="0" y="4" width="${Math.min(300, riskVal * 3)}" height="16" rx="8" fill="${colorGrad}" class="thermo-liquid"/>
                                        <line x1="75" y1="4" x2="75" y2="20" stroke="rgba(255,255,255,0.4)" stroke-width="1"/>
                                        <line x1="150" y1="4" x2="150" y2="20" stroke="rgba(255,255,255,0.6)" stroke-width="1.5"/>
                                        <line x1="225" y1="4" x2="225" y2="20" stroke="rgba(255,255,255,0.4)" stroke-width="1"/>
                                        ${bubbleBubble}
                                    </svg>
                                </div>
                            `;
                        };

                        return `
                            <div class="svg-thermo-container">
                                ${renderThermoRow('美国', usBM, usRisk, false)}
                                ${renderThermoRow('中国', cnBM, cnRisk, true)}
                            </div>
                        `;
                    })()}
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

            <!-- 4. SVG 雷达扫掠 AI 四象限投资时钟 & 历史周期比对 -->
            <div class="ai-middle-grid" style="margin-bottom: 16px;">
                <!-- 左侧：SVG 雷达扫掠投资时钟 -->
                <div class="card" style="padding: 16px;">
                    <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none; display: flex; justify-content: space-between; align-items: center;">
                        <div class="card-title"><i data-lucide="clock" width="16" style="vertical-align: middle;"></i> AI 四象限投资时钟 (Radar Map)</div>
                        <button class="info-btn" id="info-ai-clock" title="时钟说明" style="display: inline-flex; align-items: center;"><i data-lucide="help-circle" width="14"></i></button>
                    </div>
                    ${(() => {
                        const usPctX = investment_clock?.us_position?.x || 68;
                        const usPctY = investment_clock?.us_position?.y || 82;
                        const cnPctX = investment_clock?.cn_position?.x || 48;
                        const cnPctY = investment_clock?.cn_position?.y || 62;

                        // 将 0~100 映射到 SVG (cx=160, cy=100, W=320, H=200)
                        const usX = (usPctX / 100) * 240 + 40; 
                        const usY = ((100 - usPctY) / 100) * 140 + 30; 
                        const cnX = (cnPctX / 100) * 240 + 40;
                        const cnY = ((100 - cnPctY) / 100) * 140 + 30;

                        return `
                            <div class="svg-clock-box" style="height: 200px;">
                                <svg viewBox="0 0 320 200" class="svg-clock-chart">
                                    <defs>
                                        <radialGradient id="radar-sweep-grad" cx="50%" cy="50%" r="50%">
                                            <stop offset="0%" stop-color="rgba(59,130,246,0.35)"/>
                                            <stop offset="100%" stop-color="rgba(59,130,246,0.0)"/>
                                        </radialGradient>
                                    </defs>
                                    <!-- 十字坐标轴 -->
                                    <line x1="160" y1="15" x2="160" y2="185" stroke="rgba(203,213,225,0.6)" stroke-width="1" stroke-dasharray="4 4"/>
                                    <line x1="20" y1="100" x2="300" y2="100" stroke="rgba(203,213,225,0.6)" stroke-width="1" stroke-dasharray="4 4"/>
                                    
                                    <!-- 同心圆轨道 -->
                                    <circle cx="160" cy="100" r="45" fill="none" stroke="rgba(226,232,240,0.8)" stroke-width="1"/>
                                    <circle cx="160" cy="100" r="80" fill="none" stroke="rgba(226,232,240,0.5)" stroke-width="1"/>
                                    
                                    <!-- 360° 雷达旋转扫掠 -->
                                    <path d="M 160 100 L 160 20 A 80 80 0 0 1 240 100 Z" fill="url(#radar-sweep-grad)" class="radar-sweep-arc" style="transform-origin: 160px 100px;"/>
                                    
                                    <!-- 4 象限边角标签 (避开坐标打点) -->
                                    <text x="22" y="24" font-size="10" fill="var(--text-tertiary)" font-weight="600">泡沫期</text>
                                    <text x="215" y="24" font-size="10" fill="#059669" font-weight="700">硬件与能源爆发期</text>
                                    <text x="22" y="185" font-size="10" fill="var(--text-tertiary)" font-weight="600">需求验证期</text>
                                    <text x="215" y="185" font-size="10" fill="#2563eb" font-weight="600">应用爆发期</text>

                                    <!-- 中美连线 -->
                                    <line x1="${usX}" y1="${usY}" x2="${cnX}" y2="${cnY}" stroke="rgba(59,130,246,0.5)" stroke-width="1.5" stroke-dasharray="3 3"/>

                                    <!-- 美国打点 -->
                                    <g transform="translate(${usX}, ${usY})">
                                        <circle r="6" fill="#2563eb" class="clock-point-pulse"/>
                                        <rect x="8" y="-10" width="125" height="18" rx="4" fill="rgba(255,255,255,0.92)" stroke="rgba(37,99,235,0.3)"/>
                                        <text x="12" y="2" font-size="9" font-weight="700" fill="#1e40af">美 (${investment_clock?.us_position?.stage})</text>
                                    </g>

                                    <!-- 中国打点 -->
                                    <g transform="translate(${cnX}, ${cnY})">
                                        <circle r="6" fill="#dc2626" class="clock-point-pulse"/>
                                        <rect x="8" y="-10" width="115" height="18" rx="4" fill="rgba(255,255,255,0.92)" stroke="rgba(220,38,38,0.3)"/>
                                        <text x="12" y="2" font-size="9" font-weight="700" fill="#991b1b">中 (${investment_clock?.cn_position?.stage})</text>
                                    </g>
                                </svg>
                            </div>
                        `;
                    })()}
                </div>

                <!-- 右侧：AI 历史周期比对 -->
                <div class="card" style="padding: 16px;">
                    <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none;">
                        <div class="card-title"><i data-lucide="history" width="16" style="vertical-align: middle;"></i> 历史科技周期推演映射</div>
                    </div>
                    ${historical_match ? `
                        <div class="history-box">
                            <div class="history-match-era">${historical_match.matched_era}</div>
                            <div class="history-sim-bar">
                                <span>周期相似度: <strong>${historical_match.similarity_pct}%</strong></span>
                                <span>${historical_match.bubble_distance}</span>
                            </div>
                            <div class="history-summary">${historical_match.summary}</div>
                        </div>
                    ` : ''}
                </div>
            </div>

        <!-- 5. 产业链五阶段扩散 Roadmap (SVG 动态管道流 - 无重叠清爽版) -->
        <div class="card" style="margin-bottom: 16px; padding: 16px;">
            <div class="card-header" style="margin-bottom: 12px; padding-bottom: 0; border-bottom: none; display: flex; justify-content: space-between; align-items: center;">
                <div class="card-title"><i data-lucide="git-commit" width="16" style="vertical-align: middle;"></i> AI 产业链五阶段扩散模型 (SVG Pipeline Flow)</div>
                <span style="font-size: 11px; background: rgba(59,130,246,0.15); color: #60a5fa; padding: 2px 8px; border-radius: 4px;">2026 演进：具身智能与工业落地验证中</span>
            </div>
            <div class="svg-pipeline-box">
                <svg viewBox="0 0 750 115" class="svg-pipeline-chart">
                    <defs>
                        <linearGradient id="pipe-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stop-color="#10b981" />
                            <stop offset="35%" stop-color="#3b82f6" />
                            <stop offset="70%" stop-color="#8b5cf6" />
                            <stop offset="100%" stop-color="#ef4444" />
                        </linearGradient>
                    </defs>

                    <!-- 连接管道基底线 -->
                    <line x1="75" y1="58" x2="675" y2="58" stroke="rgba(226,232,240,0.8)" stroke-width="8" stroke-linecap="round"/>
                    <!-- 动态光波流动线 -->
                    <line x1="75" y1="58" x2="675" y2="58" stroke="url(#pipe-grad)" stroke-width="6" stroke-linecap="round" class="pipe-flow-line"/>

                    <!-- 节点 1: 能源与算力 -->
                    <g transform="translate(75, 58)">
                        <circle r="20" fill="#ecfdf5" stroke="#10b981" stroke-width="3"/>
                        <circle r="16" fill="none" stroke="#10b981" class="node-pulse-ring"/>
                        <text y="4" text-anchor="middle" font-size="11" font-weight="800" fill="#059669">01</text>
                        <text y="-32" text-anchor="middle" font-size="11" font-weight="700" fill="#059669">阶段 1: 能源与算力芯片</text>
                        <text y="38" text-anchor="middle" font-size="10" font-weight="600" fill="#10b981">GEV / NVDA / ARM</text>
                    </g>

                    <!-- 节点 2: 存储封装 -->
                    <g transform="translate(225, 58)">
                        <circle r="20" fill="#eff6ff" stroke="#3b82f6" stroke-width="3"/>
                        <circle r="16" fill="none" stroke="#3b82f6" class="node-pulse-ring"/>
                        <text y="4" text-anchor="middle" font-size="11" font-weight="800" fill="#1d4ed8">02</text>
                        <text y="-32" text-anchor="middle" font-size="11" font-weight="700" fill="#1d4ed8">阶段 2: 存储与先进封装</text>
                        <text y="38" text-anchor="middle" font-size="10" font-weight="600" fill="#3b82f6">美光 MU / 台积电</text>
                    </g>

                    <!-- 节点 3: 基建电源 -->
                    <g transform="translate(375, 58)">
                        <circle r="20" fill="#eff6ff" stroke="#3b82f6" stroke-width="3"/>
                        <circle r="16" fill="none" stroke="#3b82f6" class="node-pulse-ring"/>
                        <text y="4" text-anchor="middle" font-size="11" font-weight="800" fill="#1d4ed8">03</text>
                        <text y="-32" text-anchor="middle" font-size="11" font-weight="700" fill="#1d4ed8">阶段 3: 基建与液冷电源</text>
                        <text y="38" text-anchor="middle" font-size="10" font-weight="600" fill="#3b82f6">SMCI / VRT / DELL</text>
                    </g>

                    <!-- 节点 4: Agent & 具身智能 -->
                    <g transform="translate(525, 58)">
                        <circle r="18" fill="#f5f3ff" stroke="#8b5cf6" stroke-width="2.5"/>
                        <text y="4" text-anchor="middle" font-size="11" font-weight="800" fill="#6d28d9">04</text>
                        <text y="-32" text-anchor="middle" font-size="11" font-weight="700" fill="#6d28d9">阶段 4: Agent 与具身智能</text>
                        <text y="38" text-anchor="middle" font-size="10" font-weight="600" fill="#8b5cf6">PLTR / 机器人 / SaaS</text>
                    </g>

                    <!-- 节点 5: 概念炒作 -->
                    <g transform="translate(675, 58)">
                        <circle r="18" fill="#fef2f2" stroke="#ef4444" stroke-width="2.5"/>
                        <text y="4" text-anchor="middle" font-size="11" font-weight="800" fill="#b91c1c">05</text>
                        <text y="-32" text-anchor="middle" font-size="11" font-weight="700" fill="#b91c1c">阶段 5: 概念炒作 (泡沫)</text>
                        <text y="38" text-anchor="middle" font-size="10" font-weight="600" fill="#ef4444">边缘垃圾小票</text>
                    </g>
                </svg>
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

