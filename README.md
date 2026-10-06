# Zectrix Bazi Daily

Zectrix NOTE4 墨水屏「八字每日运势」插件，输出原生 400x300 1-bit（纯黑/白）PNG，页面固定第 4 页。

固定八字档案：`癸亥年 乙卯月 癸亥日 戊午时`（男）。

字体：`assets/fonts/Zfull.ttf` 点阵字体（与 zectrix-morning-brief、zectrix-nba-board 共用），1:1 绘制，1BPP 下最清晰。

## 信息源与依据

| 区域 | 数据 | 来源 / 依据 |
|---|---|---|
| 左栏·农历 | 八月廿六 等 | `lunar_python` 排本日，`getMonthInChinese()+getDayInChinese()` |
| 左栏·日干支 | 癸丑 | `lunar_python` `getDayGan()+getDayZhi()` |
| 左栏·建除 | 定日 | `lunar_python` `getZhiXing()`（十二建星） |
| 左栏·值神 | 勾陈 | `lunar_python` `getDayTianShen()`（黄黑道） |
| 左栏·冲煞 | 冲羊·煞东 | `lunar_python` `getDayChongShengXiao()` + `getDaySha()` |
| 左栏·彭祖百忌 | 癸不词讼理弱敌强 / 丑不冠带主不还乡 | `lunar_python` `getPengZuGan()/getPengZuZhi()`，保留完整 8 字 |
| 底栏·喜神 | 东南 | `lunar_python` `getPositionXiDesc()`（按当日日干查传统口诀） |
| 底栏·财神 | 正南 | `lunar_python` `getPositionCaiDesc()` |
| 底栏·吉色 | 绿色 | 固定八字档案喜用神（木→绿），`ARCHIVE['jilv_color']` |
| 右栏·评分/判语 | 综合68 / 事业75 / 财运60 / 感情65 / 比肩当值宜守成… | 当日日干 × 建除简表推演（`SCORING` + `JIANCHU_LINES`），属个人化简表，可手动覆盖 |
| 顶栏·命盘 | 癸亥年 乙卯月 癸亥日 戊午时·男 | `ARCHIVE` 固定档案，**建议专业排盘工具生成后填入**，勿依赖 AI 自动推算 |

> 左栏黄历为公开历法信息（当日黄历，不含个人命盘），可信赖。
> 右栏评分/判语为「固定档案 × 当日干支」的简表推演，仅供参考，可按需手动覆盖。

## 用法

```bash
# 安装依赖
cd /root/services/zectrix-bazi-daily
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 仅出图（调试，不推送）
.venv/bin/python scripts/make_display.py --date 2026-10-06 --out /tmp/bazi.png

# 出图并推送到设备第 4 页
.venv/bin/python scripts/make_display.py --date 2026-10-06 --out /tmp/bazi.png --push

# 禁用推送（即使带 --push）
ZECTRIX_NO_PUSH=1 .venv/bin/python scripts/make_display.py --push
```

主要参数（不传则按当日自动计算，可手动覆盖）：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--birth` | 癸亥年 乙卯月 癸亥日 戊午时 | 生辰八字四柱（建议专业工具生成后填入） |
| `--gender` | 男 | 性别（男/女） |
| `--date` | 今天 | 显示日期 YYYY-MM-DD |
| `--out` | /tmp/zectrix-bazi-daily.png | 输出 PNG 路径 |
| `--push` | 关 | 渲染后推送到 Zectrix 设备 |
| `--page` | 4 | Zectrix 页面 ID |
| `--score/--bars/--line1/--line2/--leftlabel` | 自动 | 右栏评分/判语（可覆盖） |
| `--lunar/--daygz/--jianchu/--zhishen/--chongsha/--bz1/--bz2` | 自动 | 左栏黄历（可覆盖） |
| `--foot1/--foot2/--foot3` | 自动 | 底栏喜神/财神/吉色（可覆盖） |

## 推送到设备

推送依赖 Zectrix 云端 API 配置，默认复用 `~/.config/zectrix-morning-brief/config.json`
（含 `api_key` + `device_id`），可用环境变量 `ZECTRIX_BAZI_CONFIG_DIR` 指向独立配置文件。

页面分配（NOTE4 共 4 页）：**1=晨报、3=NBA、4=八字**。`--page` 默认 4。

推送端点：`POST https://cloud.zectrix.com/open/v1/devices/<MAC>/display/image`，
multipart 字段 `pageId=4`、`dither=false`、`images=<png>`。

## GitHub 版本管理与安装到 VPS

### 1. 初始化仓库（首次）

```bash
cd /root/services/zectrix-bazi-daily
git init
git add -A
git commit -m "bazi-daily: 400x300 1BPP 八字运势插件（lunar_python 黄历 + 自动推演）"
# 远端（建议与 morning-brief / nba-board 同一命名空间，走 SSH key）
git remote add origin git@github.com:<GITHUB_USER>/zectrix-bazi-daily.git
git push -u origin main
```

> 本机已有 `~/.ssh/id_ed25519_nba` SSH key 可认证 `happynailinzz` 账号；
> 创建新仓库需要 GitHub API 权限（Personal Access Token，勾选 repo 权限），
> 或用 `gh repo create` 一次即可。

### 2. 安装到 VPS（新机器或首次部署）

```bash
# 创建部署目录（与 sibling 项目同级，便于共用字体）
mkdir -p /root/services
cd /root/services
git clone git@github.com:<GITHUB_USER>/zectrix-bazi-daily.git

# 建 venv + 装依赖
cd zectrix-bazi-daily
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 字体：本仓库已自带 assets/fonts/Zfull.ttf；
# 若缺失可软链 sibling 项目字体：
ln -sf /root/services/zectrix-morning-brief/assets/fonts/Zfull.ttf \
       /root/services/zectrix-bazi-daily/assets/fonts/Zfull.ttf
```

### 3. 复用 Zectrix 配置（推送凭据）

```bash
# 复用晨报项目的 API key / device id
export ZECTRIX_BAZI_CONFIG_DIR="$HOME/.config/zectrix-morning-brief"
# 或为八字项目建独立配置目录（含 api_key/device_id 的 config.json）
```

> ⚠️ `config.json` 含 API Key，权限应为 0600，勿提交进 git（`.gitignore` 已排除 `~/.config` 类文件；
> 项目目录内的 `assets/fonts/Zfull.ttf` 字体可以提交，字体无密）。

### 4. 更新版本（VPS 拉取最新）

```bash
cd /root/services/zectrix-bazi-daily
git pull origin main
.venv/bin/pip install -r requirements.txt   # 依赖有变更时
```

## 定制 cron 任务（每日 6:50 推送）

### 1. 使用项目自带的 cron 包装脚本

`scripts/run_scheduled.sh` 已内置：锁文件防并发、日志轮转（1MB）、TZ=Asia/Shanghai、失败记录。

```bash
chmod +x /root/services/zectrix-bazi-daily/scripts/run_scheduled.sh
```

### 2. 写入 crontab（每日 6:50 推送一次）

```bash
crontab -e
# 追加下面这一行（每天 6:50）：
50 6 * * * /root/services/zectrix-bazi-daily/scripts/run_scheduled.sh
```

### 3. 验证

```bash
# 立即手动跑一次（看日志）
/root/services/zectrix-bazi-daily/scripts/run_scheduled.sh
tail -f /var/log/zectrix-bazi-daily.log

# 查看已安装的 cron 条目
crontab -l | grep zectrix-bazi-daily
```

### cron 表达式速查

| 需求 | 表达式 |
|---|---|
| 每天 6:50 | `50 6 * * *` |
| 每天 6:50 和 18:50 | `50 6,18 * * *` |
| 工作日 6:50 | `50 6 * * 1-5` |
| 每小时 | `0 * * * *` |

> `run_scheduled.sh` 内 `--push --page 4` 已固定推送第 4 页；
> 若要改推送时间以外的内容（如换档案、换评分），直接编辑包装脚本里的命令行。

## 版式说明

- 顶栏：全宽黑条，白字上下居中；顶栏下方一行小字显示命盘档案（`命盘 四柱 · 性别`，超宽自动截断）。
- 底栏：全宽黑条，三项白字上下居中。
- 左栏「今日黄历」：圆角卡片，六行黄历信息 + 圆角宜忌黑条；上沿与右栏标题同行，底边与右栏最后一行解签同底。
- 右栏「今日运势」：标题 + 大数字评分（居中于顶栏与横线之间）+ 四条圆角进度条 + 居中解签两行。
- 1-bit 量化：`>130 灰度 → 白，否则 → 黑`。
