from __future__ import annotations

from pathlib import Path

YEARS = list(range(2015, 2025))
BRENT = [52.32, 43.64, 54.13, 71.34, 64.30, 41.96, 70.86, 100.93, 82.49, 80.52]
GAS92 = [6727, 5676, 6307, 7836, 6805, 5657, 7689, 8986, 8766, 8480]

# Sources:
# 1) U.S. Energy Information Administration, Europe Brent Spot Price FOB (Annual)
#    https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=a&n=pet&s=rbrte
# 2) Chinese 92# gasoline annual averages compiled from an industry report snippet surfaced via web search:
#    2015-2024 values = 6727, 5676, 6307, 7836, 6805, 5657, 7689, 8986, 8766, 8480 (yuan/ton)

WIDTH = 1400
HEIGHT = 820
MARGIN_LEFT = 120
MARGIN_RIGHT = 160
MARGIN_TOP = 90
MARGIN_BOTTOM = 110
PLOT_W = WIDTH - MARGIN_LEFT - MARGIN_RIGHT
PLOT_H = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM


def scale_points(values: list[float], vmin: float, vmax: float) -> list[float]:
    out = []
    for value in values:
        ratio = 0 if vmax == vmin else (value - vmin) / (vmax - vmin)
        y = MARGIN_TOP + PLOT_H - ratio * PLOT_H
        out.append(y)
    return out


def x_positions(n: int) -> list[float]:
    step = PLOT_W / (n - 1)
    return [MARGIN_LEFT + step * i for i in range(n)]


def polyline(xs: list[float], ys: list[float]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))


def extrema(values: list[float]) -> tuple[int, int]:
    return values.index(min(values)), values.index(max(values))


def y_ticks(vmin: float, vmax: float, count: int = 6) -> list[float]:
    step = (vmax - vmin) / (count - 1)
    return [vmin + step * i for i in range(count)]


def main() -> None:
    xs = x_positions(len(YEARS))
    left_min, left_max = 35.0, 110.0
    right_min, right_max = 5000.0, 9500.0
    brent_ys = scale_points(BRENT, left_min, left_max)
    gas_ys = scale_points(GAS92, right_min, right_max)
    brent_min_i, brent_max_i = extrema(BRENT)
    gas_min_i, gas_max_i = extrema(GAS92)

    lines = []
    add = lines.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">')
    add('<defs>')
    add('<style>')
    add('text { font-family: "Noto Sans CJK SC", "Microsoft YaHei", "PingFang SC", Arial, sans-serif; fill: #1f2937; }')
    add('.title { font-size: 28px; font-weight: 700; }')
    add('.subtitle { font-size: 14px; fill: #4b5563; }')
    add('.axis { font-size: 14px; fill: #374151; }')
    add('.tick { font-size: 13px; fill: #6b7280; }')
    add('.legend { font-size: 14px; }')
    add('.label { font-size: 13px; font-weight: 600; }')
    add('</style>')
    add('</defs>')
    add(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff" rx="18" ry="18"/>')
    add(f'<text x="{MARGIN_LEFT}" y="48" class="title">2015-2024年国际原油与中国92#汽油价格对比图（含极值标注）</text>')
    add(f'<text x="{MARGIN_LEFT}" y="74" class="subtitle">左轴：布伦特现货年均价（美元/桶）；右轴：中国92#汽油年均价（元/吨）</text>')

    # Grid and axes
    for tick in y_ticks(left_min, left_max):
        y = scale_points([tick], left_min, left_max)[0]
        add(f'<line x1="{MARGIN_LEFT}" y1="{y:.1f}" x2="{WIDTH - MARGIN_RIGHT}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
        add(f'<text x="{MARGIN_LEFT - 16}" y="{y + 5:.1f}" text-anchor="end" class="tick">{tick:.0f}</text>')
    for tick in y_ticks(right_min, right_max):
        y = scale_points([tick], right_min, right_max)[0]
        add(f'<text x="{WIDTH - MARGIN_RIGHT + 16}" y="{y + 5:.1f}" class="tick">{tick:.0f}</text>')
    add(f'<line x1="{MARGIN_LEFT}" y1="{MARGIN_TOP}" x2="{MARGIN_LEFT}" y2="{HEIGHT - MARGIN_BOTTOM}" stroke="#9ca3af" stroke-width="1.5"/>')
    add(f'<line x1="{WIDTH - MARGIN_RIGHT}" y1="{MARGIN_TOP}" x2="{WIDTH - MARGIN_RIGHT}" y2="{HEIGHT - MARGIN_BOTTOM}" stroke="#9ca3af" stroke-width="1.5"/>')
    add(f'<line x1="{MARGIN_LEFT}" y1="{HEIGHT - MARGIN_BOTTOM}" x2="{WIDTH - MARGIN_RIGHT}" y2="{HEIGHT - MARGIN_BOTTOM}" stroke="#9ca3af" stroke-width="1.5"/>')

    for x, year in zip(xs, YEARS):
        add(f'<line x1="{x:.1f}" y1="{HEIGHT - MARGIN_BOTTOM}" x2="{x:.1f}" y2="{HEIGHT - MARGIN_BOTTOM + 8}" stroke="#9ca3af" stroke-width="1.2"/>')
        add(f'<text x="{x:.1f}" y="{HEIGHT - MARGIN_BOTTOM + 30}" text-anchor="middle" class="tick">{year}</text>')

    add(f'<text x="{MARGIN_LEFT - 72}" y="{MARGIN_TOP - 18}" class="axis" transform="rotate(-90 {MARGIN_LEFT - 72},{MARGIN_TOP - 18})">布伦特现货价（美元/桶）</text>')
    add(f'<text x="{WIDTH - MARGIN_RIGHT + 78}" y="{MARGIN_TOP - 18}" class="axis" transform="rotate(90 {WIDTH - MARGIN_RIGHT + 78},{MARGIN_TOP - 18})">92#汽油年均价（元/吨）</text>')

    # Legend
    lx = WIDTH - MARGIN_RIGHT - 320
    ly = 52
    add(f'<line x1="{lx}" y1="{ly}" x2="{lx + 34}" y2="{ly}" stroke="#2563eb" stroke-width="4" stroke-linecap="round"/>')
    add(f'<text x="{lx + 44}" y="{ly + 5}" class="legend">布伦特现货年均价</text>')
    add(f'<line x1="{lx + 170}" y1="{ly}" x2="{lx + 204}" y2="{ly}" stroke="#f97316" stroke-width="4" stroke-linecap="round"/>')
    add(f'<text x="{lx + 214}" y="{ly + 5}" class="legend">中国92#汽油年均价</text>')

    # Series
    add(f'<polyline fill="none" stroke="#2563eb" stroke-width="4" points="{polyline(xs, brent_ys)}"/>')
    add(f'<polyline fill="none" stroke="#f97316" stroke-width="4" points="{polyline(xs, gas_ys)}"/>')

    # points
    for x, y in zip(xs, brent_ys):
        add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#2563eb" stroke="#ffffff" stroke-width="1.5"/>')
    for x, y in zip(xs, gas_ys):
        add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#f97316" stroke="#ffffff" stroke-width="1.5"/>')

    def annotate(i: int, values: list[float], ys: list[float], color: str, text: str, dx: float, dy: float) -> None:
        x = xs[i]
        y = ys[i]
        tx = x + dx
        ty = y + dy
        add(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" stroke="{color}" stroke-width="1.5" stroke-dasharray="4 4"/>')
        add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#fff" stroke="{color}" stroke-width="3"/>')
        add(f'<text x="{tx:.1f}" y="{ty - 8:.1f}" class="label" fill="{color}">{text}</text>')

    annotate(brent_min_i, BRENT, brent_ys, '#2563eb', f'最低：{YEARS[brent_min_i]}年 {BRENT[brent_min_i]:.2f}', 16, 42)
    annotate(brent_max_i, BRENT, brent_ys, '#2563eb', f'最高：{YEARS[brent_max_i]}年 {BRENT[brent_max_i]:.2f}', -90, -36)
    annotate(gas_min_i, GAS92, gas_ys, '#f97316', f'最低：{YEARS[gas_min_i]}年 {GAS92[gas_min_i]}', 18, 54)
    annotate(gas_max_i, GAS92, gas_ys, '#f97316', f'最高：{YEARS[gas_max_i]}年 {GAS92[gas_max_i]}', -20, -50)

    add('</svg>')

    out = Path('charts/oil_gasoline_2015_2024.svg')
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
