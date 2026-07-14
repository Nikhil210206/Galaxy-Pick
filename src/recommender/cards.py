# src/recommender/cards.py — free, offline placeholder image
from html import escape

SERIES_COLOR = {"S": "#1428A0", "S-Ultra": "#0C1E7F", "S-FE": "#3B5BDB", "Z-Flip": "#7048E8",
                "Z-Fold": "#5F3DC4", "A": "#1098AD", "M": "#0CA678", "F": "#E8590C"}


def placeholder_svg(model_name, series):
    color = SERIES_COLOR.get(series, "#1428A0")
    label = escape(str(model_name))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="220" height="300">
      <rect width="220" height="300" rx="24" fill="{color}"/>
      <rect x="24" y="24" width="172" height="252" rx="16" fill="#ffffff" opacity="0.10"/>
      <text x="110" y="160" fill="#fff" font-size="15" font-family="sans-serif"
            text-anchor="middle">{label}</text>
    </svg>'''
