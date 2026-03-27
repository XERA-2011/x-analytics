"""
恐慌贪婪指数统一输出工具
"""

from typing import Dict, Any, Optional, List, Tuple


def clamp_score(score: float) -> float:
    """限制分数在 0-100。"""
    return min(100.0, max(0.0, score))


def score_percent_change(change_pct: float, sensitivity: float = 10.0) -> float:
    """按百分比变化线性映射到情绪分数。"""
    return clamp_score(50.0 + change_pct * sensitivity)


def score_rsi(rsi: float) -> float:
    """统一 RSI 到情绪分数的映射。30≈25, 50≈50, 70≈75。"""
    return clamp_score(50.0 + (rsi - 50.0) * 1.25)


def score_inverse_ratio(ratio: float, sensitivity: float = 60.0) -> float:
    """比值越高分数越低，用于波动率放大等恐慌型因子。"""
    return clamp_score(50.0 - (ratio - 1.0) * sensitivity)


def score_volatility_level(
    volatility_value: float,
    neutral_level: float = 20.0,
    calm_sensitivity: float = 2.0,
    stress_sensitivity: float = 2.5,
) -> float:
    """统一波动率水平映射，低波动偏贪婪，高波动偏恐慌。"""
    diff = neutral_level - volatility_value
    sensitivity = calm_sensitivity if diff >= 0 else stress_sensitivity
    return clamp_score(50.0 + diff * sensitivity)


def build_factor(
    *,
    value: Any,
    score: float,
    weight: float,
    label: Optional[str] = None,
    note: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """构建统一因子结构。"""
    payload = {
        "value": value,
        "score": round(score, 1),
        "weight": weight,
    }
    if label:
        payload["label"] = label
    if note:
        payload["note"] = note
    payload.update(extra)
    return payload


def calculate_composite_score(indicators: Dict[str, Any]) -> Optional[float]:
    """按统一结构计算加权综合得分。"""
    total_score = 0.0
    total_weight = 0.0

    for item in indicators.values():
        if not isinstance(item, dict):
            continue
        score = item.get("score")
        weight = item.get("weight")
        if score is None or weight is None:
            continue
        total_score += float(score) * float(weight)
        total_weight += float(weight)

    if total_weight <= 0:
        return None
    return total_score / total_weight


def build_fear_greed_meta(
    market: str,
    asset: str,
    methodology: str,
    source: str = "AkShare",
    cadence: str = "daily",
    comparable_scope: str = "same_market_only",
    reference_note: Optional[str] = None,
) -> Dict[str, Any]:
    """构建统一的元信息，便于前端统一展示。"""
    meta = {
        "schema": "fear_greed_v1",
        "factor_framework": "normalized_v1",
        "market": market,
        "asset": asset,
        "methodology": methodology,
        "source": source,
        "cadence": cadence,
        "comparable_scope": comparable_scope,
    }
    if reference_note:
        meta["reference_note"] = reference_note
    return meta


def build_fear_greed_response(
    *,
    score: float,
    level: str,
    description: str,
    indicators: Dict[str, Any],
    update_time: str,
    explanation: str,
    levels: List[Dict[str, Any]],
    meta: Dict[str, Any],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """构建统一成功响应。"""
    payload = {
        "score": round(score, 1),
        "level": level,
        "description": description,
        "indicators": indicators,
        "update_time": update_time,
        "explanation": explanation,
        "levels": levels,
        "meta": meta,
    }
    if extra:
        payload.update(extra)
    return payload


def build_fear_greed_error(
    *,
    error: str,
    message: str,
    update_time: str,
    meta: Dict[str, Any],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """构建统一错误响应。"""
    payload = {
        "error": error,
        "message": message,
        "update_time": update_time,
        "meta": meta,
    }
    if extra:
        payload.update(extra)
    return payload


def build_fear_greed_explanation(
    *,
    title: str,
    factors: List[Tuple[str, float, Optional[str]]],
    levels: List[Tuple[float, str, str]],
    methodology_note: str = "该指数基于技术与行情因子合成，用于观察市场情绪变化，不构成投资建议。",
) -> str:
    """构建统一的恐慌贪婪说明文案。"""
    factor_lines = []
    for label, weight, note in factors:
        suffix = f"：{note}" if note else ""
        factor_lines.append(f"• {label} ({int(weight * 100)}%){suffix}")

    level_lines = []
    for idx, (min_score, label, _desc) in enumerate(levels):
        max_score = 100 if idx == 0 else int(levels[idx - 1][0] - 1)
        level_lines.append(f"• {label}：{int(min_score)}-{max_score}")

    sections = [
        f"{title}说明：",
        "• 指数范围：0-100，数值越高表示市场情绪越偏贪婪，越低表示越偏恐慌",
        "• 计算因子：",
        "\n".join(factor_lines),
        "• 分值解读：",
        "\n".join(level_lines),
        f"• 说明：{methodology_note}",
    ]
    return "\n".join(sections)
