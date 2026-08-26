class GoldController {
    constructor() {
        this.chinaReservesData = null;
        this.spdrGoldETFData = null;
    }

    async loadData() {
        console.log('📊 加载黄金市场数据...');

        const promises = [
            api.getGoldSilverRatio().then(data => this.renderGoldSilver(data)),
            api.getMetalSpotPrices().then(data => this.renderMetalSpotPrices(data)),
            api.getGoldFearGreed().then(data => this.renderGoldFearGreed(data)),
            api.getGoldOverboughtOversold().then(data => utils.renderOverboughtOversold('gold-obo-signal', data)),
            api.getChinaGoldReserves().then(data => this.renderChinaReserves(data)),
            api.getSPDRGoldETF().then(data => this.renderSPDRGoldETF(data))
        ];

        await Promise.allSettled(promises);

        // Bind Info Button - Gold Heat
        const infoBtn = document.getElementById('info-gold-heat');
        if (infoBtn) {
            infoBtn.onclick = () => {
                utils.showInfoModal('黄金技术热度指标说明', `
<div style="font-family: var(--font-sans); color: var(--text-primary); line-height: 1.4; white-space: normal;">
    <p style="font-size: 14px; margin-bottom: 8px;">黄金技术热度指数（0-100）是一个综合技术面指标，评估黄金当前在技术面上的超买/超卖热度。数值越高代表市场越偏向超买（高热），越低代表越偏向超卖（低热）。</p>
    
    <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 4px;">1. 核心计算因子与权重</h4>
    <ul style="margin: 0 0 8px 20px; padding: 0;">
        <li style="margin-bottom: 4px;"><b>RSI (30%)</b>：14 日相对强弱指标，反映短期价格超买超卖强弱。</li>
        <li style="margin-bottom: 4px;"><b>均线偏离度 (30%)</b>：当前价格相对 50 日均线 (MA50) 的偏离百分比，衡量趋势偏离度。</li>
        <li style="margin-bottom: 4px;"><b>波动率趋势 (20%)</b>：当前 20 日波动率对比历史 60 日波动均值，反映波动率变化。</li>
        <li style="margin-bottom: 4px;"><b>当日涨跌 (20%)</b>：当日价格的百分比变动幅度。</li>
    </ul>

    <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 4px;">2. 计算与归一化逻辑</h4>
    <ul style="margin: 0 0 8px 20px; padding: 0;">
        <li style="margin-bottom: 4px;">每个因子通过公式映射转换为 0-100 的“因子得分”后，按权重加权求和得出仪表盘的<b>综合热度分（0-100）</b>。</li>
        <li style="margin-bottom: 4px;"><b>“近一年分位数”</b>是通过回溯过去 250 个交易日的历史综合热度序列，计算当前分数处于历史水位的百分比（例如 89% 表示当前比过去 89% 的时间都更热）。</li>
    </ul>

    <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 4px;">3. 下方“技术信号”强弱条</h4>
    <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px;">技术信号条（如“强烈超买 76.8”）为另一个独立的<b>多因子强弱模型</b>，融合了 MACD、KDJ、布林带等更广泛的技术因子判定，提供更敏捷的对照验证。</p>

    <p style="font-size: 11px; color: var(--text-secondary); font-style: italic; border-top: 1px solid var(--border-light); padding-top: 8px; margin: 0;">免责声明：本数据仅供参考，不构成任何投资买卖建议。</p>
</div>
                `);
            };
            infoBtn.style.display = 'flex';
        }

        // Bind China reserves Info Button
        const chinaBtn = document.getElementById('info-china-reserves');
        if (chinaBtn) {
            chinaBtn.onclick = () => {
                utils.showInfoModal('中国央行黄金储备说明', `
<div style="font-family: var(--font-sans); color: var(--text-primary); line-height: 1.4; white-space: normal;">
    <p style="font-size: 14px; margin-bottom: 8px;"><b>中国官方储备资产中的黄金持仓量：</b></p>
    <ul style="margin: 0 0 8px 20px; padding: 0;">
        <li style="margin-bottom: 4px;"><b>数据来源</b>：国家外汇管理局，按月度发布期末持有数据。</li>
        <li style="margin-bottom: 4px;"><b>换算单位</b>：1 万盎司 ≈ 0.311 吨。</li>
        <li style="margin-bottom: 4px;"><b>变动计算</b>：当前月份黄金储备 - 上一月份黄金储备 = 当月净买入量。</li>
        <li style="margin-bottom: 4px;"><b>核心逻辑</b>：央行增持黄金属于中长期主权级外汇储备多元化行为。由于央行买入往往具有极高的价格不敏感性和持续性，在历史上往往是黄金最坚实的长期价格地板支撑。</li>
    </ul>
    <p style="font-size: 11px; color: var(--text-secondary); font-style: italic; border-top: 1px solid var(--border-light); padding-top: 8px; margin: 0;">注：最新统计月度通常在每月 7 日左右披露。</p>
</div>
                `);
            };
            chinaBtn.style.display = 'flex';
        }

        // Bind Metal Prices Info Button
        const metalBtn = document.getElementById('info-metal-prices');
        if (metalBtn) {
            metalBtn.onclick = () => {
                utils.showInfoModal('现货黄金 vs COMEX 黄金期货定价说明', `
<div style="font-family: var(--font-sans); color: var(--text-primary); line-height: 1.5; white-space: normal;">
    <p style="font-size: 14px; margin-bottom: 10px;">国际贵金属市场同时存在<b>现货（Spot）</b>与<b>期货（Futures）</b>两大核心定价基准体系，价格因交割机制不同而存在正常价差：</p>
    
    <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 4px; color: #d97706;">1. 现货黄金（伦敦金 XAU / XAUUSD）</h4>
    <ul style="margin: 0 0 10px 20px; padding: 0; font-size: 13px;">
        <li style="margin-bottom: 4px;"><b>交易机制</b>：即期实物交割，无交割月份或到期日限制。</li>
        <li style="margin-bottom: 4px;"><b>应用场景</b>：全球金店首饰、银行实物金条、外汇即期交易的最通用参考基准（如目前大约 $4656 左右）。</li>
    </ul>

    <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 4px; color: #4f46e5;">2. COMEX 黄金期货（GC 主力连续）</h4>
    <ul style="margin: 0 0 10px 20px; padding: 0; font-size: 13px;">
        <li style="margin-bottom: 4px;"><b>交易机制</b>：纽约商品交易所（COMEX）集中撮合，具有未来固定月份交割（当前主力为 12 月交割的 GC26Z 合约）。</li>
        <li style="margin-bottom: 4px;"><b>远月升水（Contango）</b>：期货价格包含了未来数月的<b>资金利息成本（Cost of Carry）、实物仓储保管费与保险费</b>。因此在当前利率环境下，远期期货合约通常比即期现货高出数十美元（当前约溢价 $60~$70）。</li>
    </ul>

    <p style="font-size: 11px; color: var(--text-secondary); font-style: italic; border-top: 1px solid var(--border-light); padding-top: 8px; margin: 0;">提示：系统同时呈现两大标的，方便现货投资者与期货衍生品交易者对照参考。</p>
</div>
                `);
            };
            metalBtn.style.display = 'flex';
        }

        // Bind SPDR ETF Info Button
        const spdrBtn = document.getElementById('info-spdr-etf');
        if (spdrBtn) {
            spdrBtn.onclick = () => {
                utils.showInfoModal('SPDR Gold Trust ETF持仓说明', `
<div style="font-family: var(--font-sans); color: var(--text-primary); line-height: 1.4; white-space: normal;">
    <p style="font-size: 14px; margin-bottom: 8px;"><b>全球最大黄金 ETF (SPDR Gold Trust) 实物持仓量：</b></p>
    <ul style="margin: 0 0 8px 20px; padding: 0;">
        <li style="margin-bottom: 4px;"><b>数据来源</b>：SPDR 官方持仓每日披露，按美股交易日更新。</li>
        <li style="margin-bottom: 4px;"><b>指标属性</b>：衡量全球投机盘、公募基金、高净值个人实物买入/卖出黄金意愿的终极晴雨表。</li>
        <li style="margin-bottom: 4px;"><b>分位数逻辑</b>：持仓总量在 5 年历史中所处的水位百分比。分位数极高（>85%）通常代表多头市场极端狂热；分位数极低（<20%）通常代表抛压耗尽，容易形成中短期市场底部。</li>
    </ul>
    <p style="font-size: 11px; color: var(--text-secondary); font-style: italic; border-top: 1px solid var(--border-light); padding-top: 8px; margin: 0;">注：ETF 持仓与黄金主力价格呈现极强的同向正相关关系。</p>
</div>
                `);
            };
            spdrBtn.style.display = 'flex';
        }

        // Bind China reserves period toggle
        const chinaToggle = document.getElementById('china-reserves-toggle');
        if (chinaToggle) {
            chinaToggle.querySelectorAll('span').forEach(btn => {
                btn.onclick = (e) => {
                    const period = e.target.dataset.period;
                    chinaToggle.querySelectorAll('span').forEach(s => s.classList.remove('active'));
                    e.target.classList.add('active');
                    this.switchChinaReservesPeriod(period);
                };
            });
        }

        // Bind SPDR ETF period toggle
        const spdrToggle = document.getElementById('spdr-etf-toggle');
        if (spdrToggle) {
            spdrToggle.querySelectorAll('span').forEach(btn => {
                btn.onclick = (e) => {
                    const period = e.target.dataset.period;
                    spdrToggle.querySelectorAll('span').forEach(s => s.classList.remove('active'));
                    e.target.classList.add('active');
                    this.switchSPDRPeriod(period);
                };
            });
        }

        if (window.lucide) {
            lucide.createIcons();
        }
    }

    renderGoldSilver(data) {
        const container = document.getElementById('gold-silver-ratio');
        if (!container) return;

        if (data.error) {
            if (data._warming_up) {
                utils.renderWarmingUp('gold-silver-ratio');
            } else {
                utils.renderError('gold-silver-ratio', data.message || data.error);
            }
            return;
        }

        // Clear warming up timer on successful data load
        utils.clearWarmingUpTimer('gold-silver-ratio');

        const ratio = data.ratio;
        // const gold = data.gold; // Unused
        // const silver = data.silver; // Unused

        // Bind Info Button
        const infoBtn = document.getElementById('info-gold-ratio');
        if (infoBtn && data.explanation) {
            infoBtn.onclick = () => utils.showInfoModal('金银比 (Gold/Silver Ratio)', data.explanation);
            infoBtn.style.display = 'flex';
        }

        const advice = ratio.investment_advice;

        const html = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; width: 100%;">
                <div style="font-size: 48px; font-weight: 700; line-height: 1; margin-bottom: 8px;">${ratio.current || '--'}</div>
                
                <div style="font-size: 14px; color: var(--text-secondary); margin-bottom: ${advice ? '12px' : '24px'}; padding: 4px 12px; background: var(--bg-secondary); border-radius: 12px;">
                    ${ratio.analysis ? `${ratio.analysis.level} · ${ratio.analysis.comment}` : '--'}
                </div>

                ${advice ? `
                <div style="text-align: center; margin-bottom: 24px; padding: 0 16px;">
                    <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
                        💡 ${advice.strategy}
                    </div>
                    <div style="font-size: 11px; color: var(--text-secondary);">
                        ${advice.reasoning}
                    </div>
                </div>
                ` : ''}
                
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; width: 100%; text-align: center; gap: 8px; border-top: 1px solid var(--border-color); padding-top: 16px;">
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">历史最高</div>
                        <div style="font-weight: 600;">${ratio.historical_high || '--'}</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">历史均值</div>
                        <div style="font-weight: 600;">${ratio.historical_avg || '--'}</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">历史最低</div>
                        <div style="font-weight: 600;">${ratio.historical_low || '--'}</div>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    renderGoldFearGreed(data) {
        this.renderMetalFearGreed(data, 'gold');
    }

    renderMetalFearGreed(data, metal) {
        const container = document.getElementById(`${metal}-fear-greed`);

        if (!container) return;

        if (data.error) {
            const msg = data._warming_up ? '数据预热中，请稍后刷新' : data.message || data.error;
            utils.renderError(`${metal}-fear-greed`, msg);
            return;
        }

        // Render Gauge + Info (Unified Style)
        // Note: container is .fg-container, which has flex-direction: column and centered align

        container.innerHTML = `
            <div class="fg-gauge" id="${metal}-gauge"></div>
            <div class="fg-info" style="flex: 0 1 auto; width: 100%;">
                <div class="fg-level">${data.level}</div>
                <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin: 6px 0;">近一年分位数: ${data.percentile != null ? data.percentile + '%' : '--'}</div>
            </div>
        `;

        // Render Gauge Chart
        if (window.charts) {
            setTimeout(() => {
                charts.createFearGreedGauge(`${metal}-gauge`, {
                    score: data.score,
                    level: data.level
                });
            }, 100);
        }
    }

    renderMetalSpotPrices(data) {
        const container = document.getElementById('metal-prices');
        if (!container) return;

        // Handle error/warming_up response
        if (data && data.error) {
            const msg = data._warming_up ? '数据预热中，请稍后刷新' : data.message || data.error;
            utils.renderError('metal-prices', msg);
            return;
        }

        if (!data || !Array.isArray(data) || data.length === 0) {
            utils.renderError('metal-prices', '暂无数据');
            return;
        }

        const html = data.map(item => {
            const change = utils.formatChange(item.change_pct);
            const badgeHtml = item.badge ? `<span class="metal-type-badge metal-badge-${item.category || 'futures'}">${item.badge}</span>` : '';
            const descHtml = item.desc ? `<span class="metal-desc">${item.desc}</span>` : '';
            return `
                <div class="list-item">
                    <div class="item-main">
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span class="item-title">${item.name}</span>
                            ${badgeHtml}
                        </div>
                        <div class="item-sub" style="display: flex; gap: 6px; align-items: center; margin-top: 3px;">
                            <span>${item.unit}</span>
                            ${descHtml ? `<span style="color: var(--text-tertiary);">·</span>${descHtml}` : ''}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div class="item-value">$${utils.formatNumber(item.price)}</div>
                        <div class="item-change ${change.class}">${change.text}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    renderChinaReserves(data) {
        this.chinaReservesData = data;
        const container = document.getElementById('china-reserves-stats');
        if (!container) return;

        if (data.error) {
            const msg = data._warming_up ? '数据预热中，请稍后刷新' : data.message || data.error;
            utils.renderError('china-reserves-stats', msg);
            return;
        }

        const netChangeText = data.net_change >= 0 ? `+${data.net_change_tonnes} 吨` : `${data.net_change_tonnes} 吨`;

        const html = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; width: 100%; padding: 4px 0;">
                <div style="font-size: 32px; font-weight: 700; line-height: 1; margin-bottom: 6px; font-family: var(--font-mono);">${data.current_tonnes.toLocaleString()} <span style="font-size: 14px; font-weight: 600; color: var(--text-secondary);">吨</span></div>
                
                <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; padding: 4px 12px; background: var(--bg-secondary); border-radius: 12px; font-weight: 600;">
                    折合约 ${data.current_value.toLocaleString()} 万盎司
                </div>

                <div style="text-align: center; margin-bottom: 16px; padding: 0 12px;">
                    <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
                        💡 当月净增持：${netChangeText}
                    </div>
                    <div style="font-size: 11px; color: var(--text-secondary);">
                        近 5 年增持速度超越 ${data.percentile}% 的月份 · 数据截至 ${data.date}
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; width: 100%; text-align: center; gap: 8px; border-top: 1px solid var(--border-color); padding-top: 12px; margin-bottom: 8px;">
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">10年最高(吨)</div>
                        <div style="font-weight: 600; font-size: 13px;">${data.historical_high.toLocaleString()}</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">10年均值(吨)</div>
                        <div style="font-weight: 600; font-size: 13px;">${data.historical_avg.toLocaleString()}</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">10年最低(吨)</div>
                        <div style="font-weight: 600; font-size: 13px;">${data.historical_low.toLocaleString()}</div>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;

        // Reset toggle UI to annual view by default
        const toggle = document.getElementById('china-reserves-toggle');
        if (toggle) {
            toggle.querySelectorAll('span').forEach(s => {
                if (s.dataset.period === 'annual') s.classList.add('active');
                else s.classList.remove('active');
            });
        }

        // Render annual purchases chart initially
        if (window.charts && data.annual_history) {
            setTimeout(() => {
                charts.createChinaReservesChart('china-reserves-chart', data.annual_history);
            }, 100);
        }
    }

    renderSPDRGoldETF(data) {
        this.spdrGoldETFData = data;
        const container = document.getElementById('spdr-etf-stats');
        if (!container) return;

        if (data.error) {
            const msg = data._warming_up ? '数据预热中，请稍后刷新' : data.message || data.error;
            utils.renderError('spdr-etf-stats', msg);
            return;
        }

        const netChangeText = data.change_tonnes >= 0 ? `+${data.change_tonnes} 吨` : `${data.change_tonnes} 吨`;
        const valueBillions = (data.total_value_usd / 1e9).toFixed(1);

        const html = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; width: 100%; padding: 4px 0;">
                <div style="font-size: 32px; font-weight: 700; line-height: 1; margin-bottom: 6px; font-family: var(--font-mono);">${data.current_tonnes.toLocaleString()} <span style="font-size: 14px; font-weight: 600; color: var(--text-secondary);">吨</span></div>
                
                <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; padding: 4px 12px; background: var(--bg-secondary); border-radius: 12px; font-weight: 600;">
                    持仓市值约 $${valueBillions} 亿
                </div>

                <div style="text-align: center; margin-bottom: 16px; padding: 0 12px;">
                    <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
                        💡 今日净增仓：${netChangeText}
                    </div>
                    <div style="font-size: 11px; color: var(--text-secondary);">
                        持仓总量处于近 5 年 ${data.percentile}% 水位 · 数据截至 ${data.date}
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; width: 100%; text-align: center; gap: 8px; border-top: 1px solid var(--border-color); padding-top: 12px; margin-bottom: 8px;">
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">5年最高</div>
                        <div style="font-weight: 600; font-size: 13px;">${data.historical_high}</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">5年均值</div>
                        <div style="font-weight: 600; font-size: 13px;">${data.historical_avg}</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 2px;">5年最低</div>
                        <div style="font-weight: 600; font-size: 13px;">${data.historical_low}</div>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;

        // Reset toggle UI to annual view by default
        const toggleSpdr = document.getElementById('spdr-etf-toggle');
        if (toggleSpdr) {
            toggleSpdr.querySelectorAll('span').forEach(s => {
                if (s.dataset.period === 'annual') s.classList.add('active');
                else s.classList.remove('active');
            });
        }

        // Render SPDR holdings trend chart initially (defaults to annual)
        if (window.charts && data.annual_history) {
            setTimeout(() => {
                charts.createSPDRHoldingsChart('spdr-etf-chart', data.annual_history);
            }, 100);
        }
    }

    switchChinaReservesPeriod(period) {
        if (!this.chinaReservesData) return;
        const history = period === 'annual' ? this.chinaReservesData.annual_history : this.chinaReservesData.monthly_history;
        if (window.charts && history) {
            charts.createChinaReservesChart('china-reserves-chart', history);
        }
        const subtitle = document.getElementById('china-chart-subtitle');
        if (subtitle) {
            subtitle.textContent = period === 'annual' ? '年度净增持量 (吨)' : '月度净增持量 (吨)';
        }
    }

    switchSPDRPeriod(period) {
        if (!this.spdrGoldETFData) return;
        const history = period === 'annual' ? this.spdrGoldETFData.annual_history : this.spdrGoldETFData.monthly_history;
        if (window.charts && history) {
            charts.createSPDRHoldingsChart('spdr-etf-chart', history);
        }
        const subtitle = document.getElementById('spdr-chart-subtitle');
        if (subtitle) {
            subtitle.textContent = period === 'annual' ? '年度期末持仓总量 (吨)' : '月度期末持仓总量 (吨)';
        }
    }
}
