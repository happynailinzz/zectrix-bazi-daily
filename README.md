# Zectrix Bazi Daily

Zectrix NOTE4 墨水屏「八字每日运势」插件，输出原生 400x300 1-bit（纯黑/白）PNG，页面固定第 4 页。

固定八字档案：`癸亥年 乙卯月 癸亥日 戊午时`（男）。

字体：`assets/fonts/Zfull.ttf` 点阵字体（与 zectrix-morning-brief、zectrix-nba-board 共用），1:1 绘制，1BPP 下最清晰。

## 用法

```bash
pip install -r requirements.txt
python scripts/make_display.py --date "2026年10月06日" --out /tmp/bazi.png
```

主要参数（均有默认值，可覆盖）：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--score` | 70 | 综合评分 |
| `--bars` | 综合:70,事业:75,财运:60,感情:65 | 四个分项分数 |
| `--line1/--line2` | 比肩当值… | 解签两行 |
| `--foot1/2/3` | 喜神 东南 / 财神 正南 / 吉色 绿色 | 底栏 |
| `--lunar/--daygz/--jianchu/--zhishen/--chongsha/--bz1/--bz2` | 黄历内容 | 左栏 |

## 版式说明

- 顶栏/底栏：全宽黑条，白字上下居中。
- 左栏「今日黄历」：圆角卡片，六行黄历信息 + 圆角宜忌黑条；上沿与右栏标题同行，底边与右栏最后一行解签同底。
- 右栏「今日运势」：标题 + 大数字评分（居中于顶栏与横线之间）+ 四条圆角进度条 + 居中解签两行。
- 1-bit 量化：`>130 灰度 → 白，否则 → 黑`。
