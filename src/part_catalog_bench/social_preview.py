"""Render a crawler-friendly PNG from the same public aggregates as the site."""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LABELS = {
    "openai/gpt-6-astra": "GPT-6 Astra",
    "anthropic/claude-fable-5.1": "Claude Fable 5.1",
    "openai/gpt-5.6-sol-pro": "GPT-5.6 Sol Pro",
    "google/gemini-3.8-flash": "Gemini 3.8 Flash",
    "deepseek/deepseek-v4-flash-vision-exp": "DeepSeek V4 Vision Exp",
    "x-ai/grok-4.6": "Grok 4.6",
    "qwen/qwen3.8-max-0902": "Qwen 3.8 Max 0902",
    "qwen/qwen3.8-flash": "Qwen 3.8 Flash",
    "z-ai/glm-5.3-flash": "GLM 5.3 Flash",
    "bytedance-seed/seed-2-1-turbo": "Seed 2.1 Turbo",
}


def _font(size):
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def _frontier(rows):
    return sorted((r for r in rows if not any(
        o["cost_usd"] <= r["cost_usd"] and o["score"] >= r["score"]
        and (o["cost_usd"] < r["cost_usd"] or o["score"] > r["score"])
        for o in rows
    )), key=lambda r: r["cost_usd"])


def render_social_preview(rows: list[dict], destination: Path) -> None:
    """Create the static 1200×630 preview; never read private run artifacts."""
    image = Image.new("RGB", (1200, 630), "white")
    draw = ImageDraw.Draw(image)
    ink, muted, blue = "#152637", "#536879", "#1558d6"
    title_font, font, small = _font(34), _font(18), _font(16)
    draw.text((36, 22), "Part Catalog Bench", font=title_font, fill=ink)
    draw.text((36, 67), "AI diagram understanding: score vs. cost", font=font, fill=muted)
    if rows:
        caption = (f'{rows[0]["questions"]} questions · {rows[0]["exercises"]} exercises'
                   f' · {len(rows)} models')
        draw.text((1164, 45), caption, font=font, fill=muted, anchor="ra")
    draw.line((36, 106, 62, 106), fill=blue, width=2)
    draw.text((71, 96), "Pareto frontier", font=small, fill=muted)
    draw.text((250, 96), "Error bars: 95% confidence intervals", font=small, fill=muted)
    eligible = [r for r in rows if isinstance(r.get("cost_usd"), (int, float))
                and math.isfinite(r["cost_usd"]) and r["cost_usd"] > 0]
    if not eligible:
        draw.text((80, 300), "No complete cost data available yet.", font=font, fill=muted)
    else:
        left, right, top, bottom = 82, 1150, 155, 540
        lo = math.floor(math.log10(min(r["cost_usd"] for r in eligible)) * 2) / 2 - .18
        hi = math.ceil(math.log10(max(r["cost_usd"] for r in eligible)) * 2) / 2 + .18

        def x(cost):
            return left + (math.log10(cost) - lo) / (hi - lo) * (right - left)

        def y(score):
            return top + (1 - score) * (bottom - top)

        for percent in range(0, 101, 20):
            cy = y(percent / 100)
            draw.line((left, cy, right, cy), fill="#e2e9ef")
            draw.text((left - 12, cy), f"{percent}%", font=small, fill=muted, anchor="rm")
        for power in range(math.floor(lo), math.ceil(hi) + 1):
            for m in (1, 2, 5):
                cost = m * 10 ** power
                if lo <= math.log10(cost) <= hi:
                    cx = x(cost)
                    draw.line((cx, top, cx, bottom), fill="#edf1f5")
                    draw.text((cx, bottom + 20), f"${cost:g}", font=small,
                              fill=muted, anchor="mt")
        draw.text((left, top - 27), "Score", font=small, fill=muted)
        draw.text((600, 598), "Cost for all questions (USD · log scale)",
                  font=font, fill=muted, anchor="mm")
        efficient = _frontier(eligible)
        if len(efficient) > 1:
            draw.line([(x(r["cost_usd"]), y(r["score"])) for r in efficient],
                      fill=blue, width=2)
        occupied = []
        for row in eligible:
            cx, cy = x(row["cost_usd"]), y(row["score"])
            color = blue if row in efficient else "#58758e"
            low, high = (y(v) for v in row["ci95"])
            draw.line((cx, low, cx, high), fill="#9cadbd", width=2)
            for height in (low, high):
                draw.line((cx - 5, height, cx + 5, height), fill="#9cadbd", width=2)
            draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=color, outline="white")
            label = LABELS.get(row["model"], row["model"].split("/")[-1])
            # Keep long/future model IDs inside the card.
            while draw.textlength(label, font=small) > 310:
                label = label[:-2] + "…"
            width = draw.textlength(label, font=small)
            tx = cx + 13 if cx + width + 13 < right else cx - width - 13
            tx = max(left, tx)
            ty = max(top, cy - 24)
            for _ in range(20):
                if not any(abs(ty - by) < 21 and tx < bx + bw + 8
                           and tx + width > bx - 8 for bx, by, bw in occupied):
                    break
                ty += 22
                if ty > bottom - 20:
                    ty = top
            occupied.append((tx, ty, width))
            if abs(ty - (cy - 24)) > 1:
                draw.line((cx, cy, tx + width / 2, ty + 8), fill="#c5cfd8")
            draw.text((tx, ty), label, font=small, fill=ink, stroke_width=2,
                      stroke_fill="white")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", optimize=True)
