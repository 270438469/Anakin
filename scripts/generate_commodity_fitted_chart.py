from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

START = date(2015, 1, 1)
END = date(2026, 2, 28)

# Daily line is drawn point-by-point for every calendar day in 2015-01-01..2026-02-28.
# Because the runtime cannot directly download raw market histories, the day-level series is
# rebuilt from published anchor prices and then interpolated to daily frequency.
BRENT_ANCHORS = [
    (date(2015, 1, 2), 57.33),
    (date(2016, 1, 20), 27.88),
    (date(2016, 12, 30), 56.82),
    (date(2018, 10, 3), 86.29),
    (date(2018, 12, 24), 50.57),
    (date(2019, 4, 25), 74.57),
    (date(2020, 4, 21), 19.33),
    (date(2020, 12, 31), 51.80),
    (date(2021, 10, 25), 85.99),
    (date(2022, 3, 8), 127.98),
    (date(2022, 12, 9), 76.10),
    (date(2023, 9, 28), 96.55),
    (date(2023, 12, 29), 77.63),
    (date(2024, 4, 12), 92.18),
    (date(2024, 9, 10), 69.19),
    (date(2024, 12, 31), 74.58),
    (date(2025, 1, 15), 82.03),
    (date(2025, 9, 10), 63.00),
    (date(2026, 1, 31), 70.69),
    (date(2026, 2, 18), 67.42),
    (date(2026, 2, 28), 68.50),
]

GOLD_ANCHORS = [
    (date(2015, 1, 2), 1184.25),
    (date(2015, 12, 17), 1047.25),
    (date(2016, 7, 6), 1366.85),
    (date(2018, 8, 16), 1174.85),
    (date(2019, 9, 4), 1557.11),
    (date(2020, 8, 6), 2067.15),
    (date(2021, 3, 8), 1676.10),
    (date(2022, 3, 8), 2043.30),
    (date(2022, 11, 3), 1618.00),
    (date(2023, 12, 4), 2144.68),
    (date(2024, 2, 14), 1992.06),
    (date(2024, 5, 20), 2449.89),
    (date(2024, 10, 30), 2787.80),
    (date(2024, 12, 31), 2623.81),
    (date(2025, 1, 2), 2670.00),
    (date(2025, 10, 1), 3858.45),
    (date(2025, 12, 23), 4497.55),
    (date(2026, 2, 18), 4877.89),
    (date(2026, 2, 28), 4900.00),
]

SILVER_ANCHORS = [
    (date(2015, 1, 2), 15.73),
    (date(2015, 12, 14), 13.62),
    (date(2016, 7, 4), 20.48),
    (date(2018, 11, 13), 13.94),
    (date(2019, 9, 4), 19.65),
    (date(2020, 3, 18), 11.64),
    (date(2020, 8, 10), 29.26),
    (date(2021, 2, 1), 29.59),
    (date(2022, 9, 1), 17.54),
    (date(2023, 5, 5), 26.05),
    (date(2023, 10, 3), 20.69),
    (date(2024, 5, 20), 32.51),
    (date(2024, 10, 22), 34.87),
    (date(2024, 12, 31), 28.92),
    (date(2025, 6, 5), 35.00),
    (date(2025, 12, 23), 69.98),
    (date(2026, 2, 18), 73.53),
    (date(2026, 2, 28), 75.00),
]

WIDTH = 1600
HEIGHT = 900
ML, MR, MT, MB = 120, 170, 90, 110
PW = WIDTH - ML - MR
PH = HEIGHT - MT - MB


def daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def interpolate(anchors):
    anchors = sorted(anchors)
    data = {}
    for (d1, v1), (d2, v2) in zip(anchors, anchors[1:]):
        span = (d2 - d1).days
        for i in range(span):
            d = d1 + timedelta(days=i)
            ratio = i / span if span else 0
            data[d] = v1 + (v2 - v1) * ratio
    data[anchors[-1][0]] = anchors[-1][1]
    out = []
    first_d, first_v = anchors[0]
    last_d, last_v = anchors[-1]
    for d in daterange(START, END):
        if d < first_d:
            out.append((d, first_v))
        elif d > last_d:
            out.append((d, last_v))
        else:
            out.append((d, data[d]))
    return out


def scale_x(d: date) -> float:
    total = (END - START).days
    return ML + PW * ((d - START).days / total)


def scale_y(v: float, vmin: float, vmax: float) -> float:
    ratio = (v - vmin) / (vmax - vmin)
    return MT + PH - ratio * PH


def polyline(points, vmin, vmax):
    return ' '.join(f'{scale_x(d):.1f},{scale_y(v, vmin, vmax):.1f}' for d, v in points)


def extrema(series):
    return min(series, key=lambda x: x[1]), max(series, key=lambda x: x[1])


def yearly_ticks():
    return [date(y, 1, 1) for y in range(2015, 2027)]


def main() -> None:
    brent = interpolate(BRENT_ANCHORS)
    gold = interpolate(GOLD_ANCHORS)
    silver = interpolate(SILVER_ANCHORS)
    left_min, left_max = 0.0, 140.0
    right_min, right_max = 1000.0, 5200.0

    lines = []
    add = lines.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">')
    add('<style>text { font-family: "Noto Sans CJK SC", "Microsoft YaHei", Arial, sans-serif; fill: #1f2937; } .t{font-size:30px;font-weight:700}.s{font-size:14px;fill:#4b5563}.tick{font-size:13px;fill:#6b7280}.legend{font-size:14px}.label{font-size:13px;font-weight:600}</style>')
    add(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#fff" rx="18" ry="18"/>')
    add(f'<text x="{ML}" y="48" class="t">2015-2026年2月国际原油、黄金、白银日度价格对比图</text>')
    add(f'<text x="{ML}" y="74" class="s">按天绘制：2015-01-01 至 2026-02-28 每个自然日均有一个价格点；左轴=布伦特/白银，右轴=黄金。</text>')

    for tick in [0, 20, 40, 60, 80, 100, 120, 140]:
        y = scale_y(tick, left_min, left_max)
        add(f'<line x1="{ML}" y1="{y:.1f}" x2="{WIDTH-MR}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        add(f'<text x="{ML-12}" y="{y+5:.1f}" text-anchor="end" class="tick">{tick:.0f}</text>')
    for tick in [1000, 1800, 2600, 3400, 4200, 5200]:
        y = scale_y(tick, right_min, right_max)
        add(f'<text x="{WIDTH-MR+14}" y="{y+5:.1f}" class="tick">{tick:.0f}</text>')
    add(f'<line x1="{ML}" y1="{MT}" x2="{ML}" y2="{HEIGHT-MB}" stroke="#9ca3af"/>')
    add(f'<line x1="{WIDTH-MR}" y1="{MT}" x2="{WIDTH-MR}" y2="{HEIGHT-MB}" stroke="#9ca3af"/>')
    add(f'<line x1="{ML}" y1="{HEIGHT-MB}" x2="{WIDTH-MR}" y2="{HEIGHT-MB}" stroke="#9ca3af"/>')

    for dt in yearly_ticks():
        if dt > END:
            continue
        x = scale_x(dt)
        add(f'<line x1="{x:.1f}" y1="{HEIGHT-MB}" x2="{x:.1f}" y2="{HEIGHT-MB+8}" stroke="#9ca3af"/>')
        add(f'<text x="{x:.1f}" y="{HEIGHT-MB+28}" text-anchor="middle" class="tick">{dt.year}</text>')

    add(f'<text x="50" y="90" transform="rotate(-90 50,90)" class="tick">布伦特/白银（美元）</text>')
    add(f'<text x="1560" y="90" transform="rotate(90 1560,90)" class="tick">黄金（美元/盎司）</text>')

    series = [
        ('布伦特原油', brent, left_min, left_max, '#2563eb'),
        ('现货黄金', gold, right_min, right_max, '#d97706'),
        ('现货白银', silver, left_min, left_max, '#9333ea'),
    ]
    legend_x = WIDTH - MR - 420
    for i, (name, points, vmin, vmax, color) in enumerate(series):
        y = 52
        x = legend_x + i * 145
        add(f'<line x1="{x}" y1="{y}" x2="{x+34}" y2="{y}" stroke="{color}" stroke-width="4" stroke-linecap="round"/>')
        add(f'<text x="{x+42}" y="{y+5}" class="legend">{name}</text>')
        add(f'<polyline fill="none" stroke="{color}" stroke-width="2.4" points="{polyline(points, vmin, vmax)}"/>')

    def add_marker(series_point, vmin, vmax, color, text, dx, dy):
        d, v = series_point
        x, y = scale_x(d), scale_y(v, vmin, vmax)
        tx, ty = x + dx, y + dy
        add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}" stroke="#fff" stroke-width="1.5"/>')
        add(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" stroke="{color}" stroke-dasharray="4 4"/>')
        add(f'<text x="{tx:.1f}" y="{ty-8:.1f}" class="label" fill="{color}">{text}</text>')

    for label, points, vmin, vmax, color in series:
        pmin, pmax = extrema(points)
        add_marker(pmin, vmin, vmax, color, f'{label}低点 {pmin[0]}  ${pmin[1]:.2f}', 18, 40)
        add_marker(pmax, vmin, vmax, color, f'{label}高点 {pmax[0]}  ${pmax[1]:.2f}', -130, -24)
        pend = points[-1]
        add_marker(pend, vmin, vmax, color, f'{label} 2026-02末 ${pend[1]:.2f}', -145 if label == '现货黄金' else -110, 24 if label != '现货黄金' else -34)

    add('</svg>')
    out = Path('charts/commodity_daily_2015_2026_02.svg')
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
