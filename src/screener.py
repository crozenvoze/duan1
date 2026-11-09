"""Lọc và xếp hạng cổ phiếu trên bảng chỉ số đã chuẩn hóa."""

from __future__ import annotations

from typing import Any

import pandas as pd

REQUIRED_SCREEN_COLUMNS = {
    "ticker", "pe", "pb", "roe", "revenue_growth", "eps_growth",
    "debt_to_equity", "avg_value_traded", "market_cap", "industry",
}


def filter_stocks(data: pd.DataFrame, criteria: dict[str, Any]) -> pd.DataFrame:
    """Lọc theo khoảng chỉ tiêu; tiêu chí None được bỏ qua."""
    missing = REQUIRED_SCREEN_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Bảng screener thiếu cột: {', '.join(sorted(missing))}")
    result = data.copy()
    numeric_filters = {
        "pe": ("pe_min", "pe_max"),
        "pb": ("pb_min", "pb_max"),
        "roe": ("roe_min", "roe_max"),
        "revenue_growth": ("revenue_growth_min", "revenue_growth_max"),
        "eps_growth": ("eps_growth_min", "eps_growth_max"),
        "debt_to_equity": ("debt_to_equity_min", "debt_to_equity_max"),
        "avg_value_traded": ("avg_value_traded_min", "avg_value_traded_max"),
        "market_cap": ("market_cap_min", "market_cap_max"),
    }
    for column, (minimum_key, maximum_key) in numeric_filters.items():
        result[column] = pd.to_numeric(result[column], errors="coerce")
        minimum, maximum = criteria.get(minimum_key), criteria.get(maximum_key)
        if minimum is not None:
            result = result[result[column] >= minimum]
        if maximum is not None:
            result = result[result[column] <= maximum]
    industries = criteria.get("industries")
    if industries:
        result = result[result["industry"].isin(industries)]
    return result.reset_index(drop=True)


def rank_stocks(data: pd.DataFrame) -> pd.DataFrame:
    """Xếp hạng value/quality/growth/momentum bằng percentile rank trung bình.

    P/E và P/B thấp hơn được ưu tiên; ROE, doanh thu/EPS growth, momentum cao
    hơn được ưu tiên; nợ/vốn chủ thấp hơn được ưu tiên. Percentile hạn chế độ
    nhạy với đơn vị và outlier, nhưng không khắc phục sai lệch dữ liệu nguồn.
    """
    frame = data.copy()
    factors = {
        "value_score": {"pe": False, "pb": False},
        "quality_score": {"roe": True, "debt_to_equity": False},
        "growth_score": {"revenue_growth": True, "eps_growth": True},
        "momentum_score": {"momentum": True},
    }
    scores: list[str] = []
    for group, directions in factors.items():
        component_scores = []
        for column, higher_is_better in directions.items():
            if column not in frame.columns:
                continue
            numeric = pd.to_numeric(frame[column], errors="coerce")
            # ascending=True memberi percentile cao nhất cho giá trị lớn nhất;
            # với chỉ số thấp là tốt, đảo chiều xếp hạng.
            component_scores.append(numeric.rank(pct=True, ascending=higher_is_better))
        if component_scores:
            frame[group] = pd.concat(component_scores, axis=1).mean(axis=1)
            scores.append(group)
    if not scores:
        raise ValueError("Không có chỉ tiêu nào để xếp hạng.")
    frame["composite_score"] = frame[scores].mean(axis=1)
    return frame.sort_values("composite_score", ascending=False, na_position="last").reset_index(drop=True)
