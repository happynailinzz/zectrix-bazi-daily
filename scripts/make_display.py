#!/usr/bin/env python3
"""生成 400x300 1-bit 墨水屏八字运势展示图.

用法: python3 make_display.py [--date 2026-10-06] [--out bazi_20261006.png]

字体：与 bazi_daily / NBA / 晨报 项目一致的 Zfull.ttf 点阵字体，1:1 绘制。
左右栏文字上下对齐：左栏黄历标题行与右栏"今日运势"同行，左栏宜忌黑条与右栏最后一行解签同底。
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 400, 300

# --- 字体：Zfull.ttf 点阵字体 ---
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_CANDIDATES = [
    os.environ.get("ZECTRIX_FONT", ""),
    os.path.join(BASE, "assets", "fonts", "Zfull.ttf"),
    os.path.join(BASE, "..", "zectrix-morning-brief", "assets", "fonts", "Zfull.ttf"),
]
_font_path = next((p for p in FONT_CANDIDATES if p and os.path.exists(p)), None)


def font(size):
    if _font_path:
        return ImageFont.truetype(_font_path, size, index=0)
    return ImageFont.load_default()


def fit_width(draw, text, f, max_w):
    """截断超宽文本。"""
    if draw.textlength(text, font=f) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=f) > max_w:
        text = text[:-1]
    return text + "…"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026年10月06日")
    ap.add_argument("--out", default="bazi_display.png")
    ap.add_argument("--score", type=int, default=70)
    ap.add_argument("--bars", default="综合:70,事业:75,财运:60,感情:65")
    ap.add_argument("--line1", default="比肩当值宜守成，丑午害财防破耗")
    ap.add_argument("--line2", default="宜办正事理旧务，忌借贷争讼远行")
    ap.add_argument("--foot1", default="喜神 东南")
    ap.add_argument("--foot2", default="财神 正南")
    ap.add_argument("--foot3", default="吉色 绿色")
    # 左栏：当日黄历（公开信息，不含个人命盘）
    ap.add_argument("--lunar", default="八月廿六")
    ap.add_argument("--daygz", default="癸丑")
    ap.add_argument("--jianchu", default="定日")
    ap.add_argument("--zhishen", default="勾陈")
    ap.add_argument("--chongsha", default="冲羊 · 煞东")
    ap.add_argument("--bz1", default="癸不词讼")
    ap.add_argument("--bz2", default="丑不冠带")
    ap.add_argument("--leftlabel", default="宜守成 · 忌争讼")
    a = ap.parse_args()

    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)

    # 字号
    f_top = font(20)        # 顶栏标题
    f_date = font(14)       # 顶栏日期
    f_card = font(16)       # 卡片标题
    f_big = font(40)        # 综合大数字
    f_body = font(13)       # 正文
    f_small = font(12)      # 小字
    f_bar = font(13)       # 条形标签/分数
    f_foot = font(14)      # 底栏

    # 布局常量
    TOP_H = 36             # 顶栏高
    BOT_TOP = 262          # 底栏起点
    LX0, LX1 = 8, 140     # 左栏范围（加宽，可用 132px）
    RX = 150              # 右栏起点（随左栏加宽右移）

    # ---- 顶栏 ----
    d.rectangle([0, 0, W, TOP_H], fill=0)
    d.text((10, TOP_H // 2), "八字运势", font=f_top, fill=255, anchor="lm")
    d.text((W - 10, TOP_H // 2), a.date, font=f_date, fill=255, anchor="rm")

    # ---- 右：今日运势（保持原版节奏，不动） ----
    title_y = 62
    d.text((RX, title_y), "今日运势", font=f_card, fill=0, anchor="lm")
    d.text((W - 14, 57), str(a.score), font=f_big, fill=0, anchor="rm")
    d.line([RX, 78, W - 14, 78], fill=0, width=1)

    # 四条进度条（圆角），行距 28
    bars = [b.split(":") for b in a.bars.split(",")]
    bx0, bx1 = 200, 348
    R_BAR = 6
    for i, (name, val) in enumerate(bars):
        v = int(val)
        cy = 104 + i * 28
        d.text((RX, cy), name, font=f_bar, fill=0, anchor="lm")
        d.rounded_rectangle([bx0, cy - 7, bx1, cy + 7], radius=R_BAR, outline=0, width=1)
        fillx = bx0 + 1 + int((bx1 - bx0 - 2) * v / 100)
        if fillx > bx0 + 2:
            d.rounded_rectangle([bx0 + 1, cy - 5, fillx, cy + 5], radius=max(0, R_BAR - 2), fill=0)
        d.text((bx1 + 6, cy), str(v), font=f_bar, fill=0, anchor="lm")

    # 解签两行（居中）
    rcx = (RX + W - 14) // 2
    d.text((rcx, 224), fit_width(d, a.line1, f_small, W - RX - 14), font=f_small, fill=0, anchor="mm")
    d.text((rcx, 244), fit_width(d, a.line2, f_small, W - RX - 14), font=f_small, fill=0, anchor="mm")
    line2_bottom = 256  # line2 文字底边约 244+12

    # ---- 左：今日黄历（圆角卡片，内容画在边框之后） ----
    R_CARD = 12
    d.rounded_rectangle([LX0, 48, LX1, 250], radius=R_CARD, outline=0, width=1)
    cx = (LX0 + LX1) // 2
    d.text((cx, title_y), "今日黄历", font=f_card, fill=0, anchor="mm")
    d.line([LX0 + 8, 78, LX1 - 8, 78], fill=0, width=1)

    # 黄历内容 6 行，撑满 90~210（行距 24），padding 10
    rows = [
        (f"{a.lunar} · {a.daygz}日", f_small),
        (f"{a.jianchu} · {a.zhishen}", f_body),
        (a.chongsha, f_body),
        ("彭祖百忌", f_small),
        (a.bz1, f_body),
        (a.bz2, f_body),
    ]
    for i, (t, fnt) in enumerate(rows):
        cy = 90 + i * 24
        d.text((cx, cy), fit_width(d, t, fnt, LX1 - LX0 - 10), font=fnt, fill=0, anchor="mm")

    # 宜忌黑条（圆角，上抬避免与底栏边线重叠），padding 10
    R_PILL = 8
    d.rounded_rectangle([LX0 + 4, 220, LX1 - 4, 242], radius=R_PILL, fill=0)
    d.text((cx, 231), fit_width(d, a.leftlabel, f_body, LX1 - LX0 - 10), font=f_body, fill=255, anchor="mm")

    # ---- 底栏 ----
    d.rectangle([0, BOT_TOP, W, H], fill=0)
    foot_mid = (BOT_TOP + H) // 2
    for i, t in enumerate([a.foot1, a.foot2, a.foot3]):
        d.text((W * (2 * i + 1) // 6, foot_mid), fit_width(d, t, f_foot, W // 3 - 8), font=f_foot, fill=255, anchor="mm")

    # ---- 1-bit 量化 ----
    bw = img.point(lambda p: 255 if p > 130 else 0, mode="1")
    bw.convert("RGB").save(a.out)
    print("saved:", a.out, bw.size, bw.mode)


if __name__ == "__main__":
    main()
