#!/usr/bin/env python3
"""生成 400x300 1-bit 墨水屏八字运势展示图，并推送到 Zectrix 设备第 4 页.

用法:
  python3 make_display.py --out /tmp/zectrix-bazi-daily.png          # 仅出图（调试）
  python3 make_display.py --push                                     # 出图并推送到设备第 4 页
  ZECTRIX_NO_PUSH=1 python3 make_display.py                          # 禁用推送

八字档案：需填写生辰八字四柱 + 性别（--birth + --gender）。
  重要备注：AI 根据出生年月日/时自动生成八字（四柱干支）的错误概率很大，
  强烈建议使用专业八字排盘工具（如元亨利贞、八字排盘等）生成八字后，再手动填入本脚本。
  仓库内默认值为虚拟占位（甲子年 丙子月 壬子日 乙亥时，男），请勿直接用于真实测算；
  本地真实八字写在项目根目录 local_config.py（已被 .gitignore 排除，不会提交）。

数据源（cron 每日运行时自动生成，无需手动维护）：
  - 左栏黄历（lunar/daygz/jianchu/zhishen/chongsha/bz1/bz2）：lunar_python 排本日黄历
  - 喜神/财神方位：按传统口诀（日干查表）
  - 吉色：固定八字档案喜用神（木 → 绿）
  - 评分/判语/宜忌：固定八字档案的当日推演（简表，见 SCORING）

字体：Zfull.ttf 点阵字体（与 NBA / 晨报 项目一致），1:1 绘制。
左右栏文字上下对齐：左栏黄历标题行与右栏"今日运势"同行，左栏宜忌黑条与右栏最后一行解签同底。
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from PIL import Image, ImageDraw, ImageFont

try:
    from lunar_python import Solar, Lunar
    HAS_LUNAR = True
except ImportError:
    HAS_LUNAR = False

W, H = 400, 300
PAGE_ID = "4"  # NOTE4 页面：1=晨报 3=NBA 4=八字

# --- 字体：Zfull.ttf 点阵字体 ---
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_CANDIDATES = [
    os.environ.get("ZECTRIX_FONT", ""),
    os.path.join(BASE, "assets", "fonts", "Zfull.ttf"),
    os.path.join(BASE, "..", "zectrix-morning-brief", "assets", "fonts", "Zfull.ttf"),
]
_font_path = next((p for p in FONT_CANDIDATES if p and os.path.exists(p)), None)

# --- 八字档案（仓库内为虚拟占位值；本地真实值由 local_config.py 覆盖，勿提交） ---
ARCHIVE = {
    "birth": "甲子年 丙子月 壬子日 乙亥时",
    "gender": "男",
    "xiyong": "木",
    "jilv_color": "绿色",
}


def _load_local_archive():
    """加载项目根目录 local_config.py（被 .gitignore 排除）里的真实八字档案。"""
    global ARCHIVE
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_path = os.path.join(base, "local_config.py")
    if os.path.exists(local_path):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("zectrix_bazi_local", local_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            local = getattr(mod, "LOCAL_ARCHIVE", None) or {}
            for key in ("birth", "gender", "xiyong", "jilv_color"):
                if key in local:
                    ARCHIVE[key] = local[key]
        except Exception as e:
            print(f"WARN: local_config.py 加载失败（{e}），使用仓库虚拟八字", file=sys.stderr)


_load_local_archive()

# --- 日干 → 喜神/财神 传统口诀 ---
GANS = "甲乙丙丁戊己庚辛壬癸"
XISHEN = {"甲": "东北", "乙": "正东北", "丙": "西南", "丁": "正西",
          "戊": "东南", "己": "东北", "庚": "西方", "辛": "西南",
          "壬": "正南", "癸": "东南"}
CAISHEN = {"甲": "东北", "乙": "东北", "丙": "西南", "丁": "正西",
           "戊": "正南", "己": "正南", "庚": "西方", "辛": "西南",
           "壬": "正南", "癸": "正南"}


def auto_data(date: dt.date):
    """用 lunar_python 生成当日黄历数据；不可用时回退默认值。"""
    defaults = {
        "lunar": "八月廿六", "daygz": "癸丑", "jianchu": "定日",
        "zhishen": "勾陈", "chongsha": "冲羊 · 煞东",
        "bz1": "癸不词讼", "bz2": "丑不冠带",
        "foot1": "喜神 东南", "foot2": "财神 正南",
    }
    if not HAS_LUNAR:
        print("WARN: lunar_python 未安装，黄历使用默认值", file=sys.stderr)
        return defaults
    try:
        solar = Solar.fromYmd(date.year, date.month, date.day)
        lunar = solar.getLunar()
        gan = lunar.getDayGan()
        zhi = lunar.getDayZhi()
        chong_animal = lunar.getDayChongShengXiao()
        sha_dir = lunar.getDaySha()
        jianchu = lunar.getZhiXing()  # 建除（十二建星：建除满平定执破危成收开闭）
        tianshen = lunar.getDayTianShen()  # 天神（值神）
        p_gan = lunar.getPengZuGan()
        p_zhi = lunar.getPengZuZhi()
        # 喜神/财神：lunar_python 直接提供
        xi_dir = lunar.getPositionXiDesc()
        cai_dir = lunar.getPositionCaiDesc()
        defaults.update({
            "lunar": lunar.getMonthInChinese() + "月" + lunar.getDayInChinese(),
            "daygz": f"{gan}{zhi}",
            "jianchu": f"{jianchu}日",
            "zhishen": tianshen,
            "chongsha": f"冲{chong_animal} · 煞{sha_dir}",
            "bz1": p_gan[:8],
            "bz2": p_zhi[:8],
            "foot1": f"喜神 {xi_dir}" if xi_dir else defaults["foot1"],
            "foot2": f"财神 {cai_dir}" if cai_dir else defaults["foot2"],
        })
        return defaults
    except Exception as e:
        print(f"WARN: 黄历数据生成失败（{e}），使用默认值", file=sys.stderr)
        return defaults


# --- 当日运势推演（简表：日干 × 建除 维度评分 + 判语） ---
# 综合 = 各维度均值；事业/财运/感情 维度评分，score = 四维均值
SCORING = {
    # 日干 → (事业, 财运, 感情) 基准分（以癸水为例：事业75 财运60 感情65）
    "癸": (75, 60, 65),
    "戊": (70, 68, 62),
    "甲": (78, 64, 70),
    "乙": (72, 70, 68),
}
# 建除 → 判语模板（day_gz 天干决定"当值"，建除决定行为建议）
JIANCHU_LINES = {
    "定": ("比肩当值宜守成，{harm}防破耗", "宜办正事理旧务，忌借贷争讼远行"),
    "建": ("建日宜开业，宜动不利静", "宜开拓新业务，忌旧账旧务纠缠"),
    "除": ("除日宜治病，宜清理旧账", "宜除旧布新，忌远行搬家"),
    "满": ("满日宜祭祀，忌远行", "宜祭祀祈福，忌词讼远行"),
    "平": ("平日宜平顺，忌大兴土木", "宜守成稳进，忌重大投资"),
    "收": ("收日宜纳财，忌开仓", "宜收款结账，忌散财借贷"),
    "危": ("危日宜避险，忌登高远行", "宜保守避祸，忌冒险决策"),
    "成": ("成日宜嫁娶，宜开业", "宜成事签约，忌翻旧账"),
    "开": ("开日宜求医，忌动土", "宜求医就医，忌破土兴工"),
    "闭": ("闭日宜葬埋，忌远行", "宜收尾结案，忌开张纳财"),
}
HARM = {"丑": "丑午害财", "未": "丑未冲财", "戌": "戌未破财"}  # 日支相害提示


def auto_score(date: dt.date, huanli) -> dict:
    """由当日干支 + 固定档案推演评分与判语。"""
    day_gz = huanli["daygz"]
    gan, zhi = day_gz[0], day_gz[1]
    base = SCORING.get(gan, (70, 65, 65))
    bars = {"事业": base[0], "财运": base[1], "感情": base[2]}
    bars["综合"] = round((bars["事业"] + bars["财运"] + bars["感情"] + 70) / 4)
    jc = huanli["jianchu"].rstrip("日")
    l1, l2 = JIANCHU_LINES.get(jc, JIANCHU_LINES["定"])
    harm = HARM.get(zhi, "丑午害财")
    return {
        "score": bars["综合"],
        "bars": ",".join(f"{k}:{v}" for k, v in bars.items()),
        "line1": l1.format(harm=harm),
        "line2": l2,
        "leftlabel": "宜守成 · 忌争讼" if jc == "定" else "宜顺势 · 忌妄动",
    }


def build_config(date: dt.date) -> dict:
    huanli = auto_data(date)
    sc = auto_score(date, huanli)
    date_cn = f"{date.year}年{date.month:02d}月{date.day:02d}日"
    return {
        "date": date_cn,
        "birth": ARCHIVE["birth"],
        "gender": ARCHIVE["gender"],
        "score": sc["score"],
        "bars": sc["bars"],
        "line1": sc["line1"],
        "line2": sc["line2"],
        "foot1": huanli["foot1"],
        "foot2": huanli["foot2"],
        "foot3": f"吉色 {ARCHIVE['jilv_color']}",
        "lunar": huanli["lunar"],
        "daygz": huanli["daygz"],
        "jianchu": huanli["jianchu"],
        "zhishen": huanli["zhishen"],
        "chongsha": huanli["chongsha"],
        "bz1": huanli["bz1"],
        "bz2": huanli["bz2"],
        "leftlabel": sc["leftlabel"],
    }


def load_zectrix_config():
    """复用 morning-brief 的 zectrix API 配置（含 api_key / device_id）。"""
    cfg_dir = os.environ.get(
        "ZECTRIX_BAZI_CONFIG_DIR",
        os.path.expanduser("~/.config/zectrix-morning-brief"),
    )
    cfg_file = os.path.join(cfg_dir, "config.json")
    if not os.path.exists(cfg_file):
        return None
    with open(cfg_file) as f:
        return json.load(f)


def push_zectrix(config, image_path: str, page_id: str = PAGE_ID):
    """把 PNG 推送到 Zectrix 设备指定页面。"""
    api_key = config.get("api_key")
    device_id = config.get("device_id")
    if not api_key or not device_id:
        print("WARN: 未配置 zectrix api_key/device_id，跳过推送", file=sys.stderr)
        return False
    BASE = "https://cloud.zectrix.com/open/v1"
    with open(image_path, "rb") as f:
        payload = f.read()
    boundary = "----ZectrixBaziDaily" + os.urandom(8).hex()
    parts = []
    for key, value in (("pageId", page_id), ("dither", "false")):
        parts.append(
            ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
             % (boundary, key, value)).encode()
        )
    parts.append(
        ("--%s\r\nContent-Disposition: form-data; name=\"images\"; "
         "filename=\"bazi-daily.png\"\r\nContent-Type: image/png\r\n\r\n"
         % boundary).encode() + payload + b"\r\n"
    )
    body = b"".join(parts) + ("--%s--\r\n" % boundary).encode()
    url = "%s/devices/%s/display/image" % (BASE, urllib.parse.quote(device_id, safe=":"))
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"X-API-Key": api_key,
                 "Content-Type": "multipart/form-data; boundary=%s" % boundary},
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("code") != 0:
        raise RuntimeError(f"推送失败：{result}")
    print(f"PUSH pageId={page_id} OK")
    return True


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
    ap = argparse.ArgumentParser(
        description="生成 400x300 1-bit 墨水屏八字运势展示图。"
        "八字四柱请由专业排盘工具生成后填入，勿依赖 AI 自动推算。"
    )
    # ---- 八字档案（必填项：生辰八字 + 性别） ----
    ap.add_argument("--birth", default=ARCHIVE["birth"],
                   help="生辰八字四柱（年/月/日/时），建议用专业排盘工具生成")
    ap.add_argument("--gender", default=ARCHIVE["gender"], choices=["男", "女"],
                   help="性别，决定大运顺逆与喜用神取法")
    ap.add_argument("--date", default=None,
                   help="显示日期 YYYY-MM-DD（默认今天）")
    ap.add_argument("--out", default="/tmp/zectrix-bazi-daily.png")
    ap.add_argument("--push", action="store_true",
                   help="渲染后推送到 Zectrix 设备第 4 页（默认不推送，仅出图）")
    ap.add_argument("--page", default=PAGE_ID,
                   help="Zectrix 页面 ID（默认 4）")
    # 可覆盖的数据参数（不传则按当日自动计算）
    ap.add_argument("--score", type=int, default=None, help="综合评分（默认自动）")
    ap.add_argument("--bars", default=None, help="四个分项（默认自动）")
    ap.add_argument("--line1", default=None, help="解签第一行（默认自动）")
    ap.add_argument("--line2", default=None, help="解签第二行（默认自动）")
    ap.add_argument("--leftlabel", default=None, help="宜忌标签（默认自动）")
    ap.add_argument("--lunar", default=None, help="农历月日（默认自动）")
    ap.add_argument("--daygz", default=None, help="日干支（默认自动）")
    ap.add_argument("--jianchu", default=None, help="建除（默认自动）")
    ap.add_argument("--zhishen", default=None, help="值神（默认自动）")
    ap.add_argument("--chongsha", default=None, help="冲煞（默认自动）")
    ap.add_argument("--bz1", default=None, help="彭祖百忌·干（默认自动）")
    ap.add_argument("--bz2", default=None, help="彭祖百忌·支（默认自动）")
    ap.add_argument("--foot1", default=None, help="喜神（默认自动）")
    ap.add_argument("--foot2", default=None, help="财神（默认自动）")
    ap.add_argument("--foot3", default=None, help="吉色（默认取档案喜用神）")
    a = ap.parse_args()

    # ---- 组装数据：自动计算 + 手动覆盖 ----
    show_date = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    auto = build_config(show_date)
    cfg = {}
    for key in ("date", "birth", "gender", "score", "bars", "line1", "line2",
                "foot1", "foot2", "foot3", "lunar", "daygz", "jianchu",
                "zhishen", "chongsha", "bz1", "bz2", "leftlabel"):
        val = getattr(a, key, None)
        cfg[key] = val if val is not None else auto[key]
    # 手动指定了 foot3 就用手动值，否则用档案喜用神
    if cfg["foot3"] is None:
        cfg["foot3"] = auto["foot3"]

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
    d.text((W - 10, TOP_H // 2), cfg["date"], font=f_date, fill=255, anchor="rm")

    # 八字档案行（顶栏下方，小字；birth 超宽截断）
    profile_y = 46
    profile = fit_width(d, f"命盘 {cfg['birth']} · {cfg['gender']}", f_small, W - 20)
    d.text((W // 2, profile_y), profile, font=f_small, fill=0, anchor="mm")

    # ---- 右：今日运势 ----
    title_y = 62
    d.text((RX, title_y), "今日运势", font=f_card, fill=0, anchor="lm")
    d.text((W - 14, 57), str(cfg["score"]), font=f_big, fill=0, anchor="rm")
    d.line([RX, 78, W - 14, 78], fill=0, width=1)

    # 四条进度条（圆角），行距 28
    bars = [b.split(":") for b in cfg["bars"].split(",")]
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
    d.text((rcx, 224), fit_width(d, cfg["line1"], f_small, W - RX - 14), font=f_small, fill=0, anchor="mm")
    d.text((rcx, 244), fit_width(d, cfg["line2"], f_small, W - RX - 14), font=f_small, fill=0, anchor="mm")

    # ---- 左：今日黄历（圆角卡片，内容画在边框之后） ----
    R_CARD = 12
    d.rounded_rectangle([LX0, 48, LX1, 250], radius=R_CARD, outline=0, width=1)
    cx = (LX0 + LX1) // 2
    d.text((cx, title_y), "今日黄历", font=f_card, fill=0, anchor="mm")
    d.line([LX0 + 8, 78, LX1 - 8, 78], fill=0, width=1)

    # 黄历内容 6 行，撑满 90~210（行距 24），padding 10
    rows = [
        (f"{cfg['lunar']} · {cfg['daygz']}日", f_small),
        (f"{cfg['jianchu']} · {cfg['zhishen']}", f_body),
        (cfg["chongsha"], f_body),
        ("彭祖百忌", f_small),
        (cfg["bz1"], f_body),
        (cfg["bz2"], f_body),
    ]
    for i, (t, fnt) in enumerate(rows):
        cy = 90 + i * 24
        d.text((cx, cy), fit_width(d, t, fnt, LX1 - LX0 - 10), font=fnt, fill=0, anchor="mm")

    # 宜忌黑条（圆角，上抬避免与底栏边线重叠），padding 10
    R_PILL = 8
    d.rounded_rectangle([LX0 + 4, 220, LX1 - 4, 242], radius=R_PILL, fill=0)
    d.text((cx, 231), fit_width(d, cfg["leftlabel"], f_body, LX1 - LX0 - 10), font=f_body, fill=255, anchor="mm")

    # ---- 底栏 ----
    d.rectangle([0, BOT_TOP, W, H], fill=0)
    foot_mid = (BOT_TOP + H) // 2
    for i, t in enumerate([cfg["foot1"], cfg["foot2"], cfg["foot3"]]):
        d.text((W * (2 * i + 1) // 6, foot_mid), fit_width(d, t, f_foot, W // 3 - 8), font=f_foot, fill=255, anchor="mm")

    # ---- 1-bit 量化 ----
    bw = img.point(lambda p: 255 if p > 130 else 0, mode="1")
    bw.convert("RGB").save(a.out)
    print("saved:", a.out, bw.size, bw.mode)

    # ---- 推送 ----
    if a.push and os.environ.get("ZECTRIX_NO_PUSH") != "1":
        zcfg = load_zectrix_config()
        if zcfg:
            try:
                push_zectrix(zcfg, a.out, a.page)
            except Exception as e:
                print(f"PUSH FAILED: {e}", file=sys.stderr)
        else:
            print("WARN: 未找到 zectrix 配置，跳过推送", file=sys.stderr)


if __name__ == "__main__":
    main()
