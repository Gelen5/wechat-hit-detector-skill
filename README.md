# wechat-hit-detector-skill 公众号爆款检测

微信公众号文章**发布前**爆款检测 Skill。四层检测引擎：**内容六维评分 + 阅读量预测 + 受众共鸣模拟 + 微信9条红线合规 + 反AI味扫描 + 改稿建议**，一条命令输出可执行改稿清单，并自动生成苹果级暗色磨砂玻璃 HTML 可视化报告。

## 功能

| 层 | 能力 |
|---|---|
| L1 内容层 | 六维评分（标题钩子力25 / 开头钩子力20 / 内容价值度20 / 选题势能15 / 阅读体验10 / 互动转化10），**按文章风格自适应**（干货/情绪/观点/故事/资讯） |
| L2 数据层 | 阅读量预测：粉丝数 × 账号基准打开率 × 标题修正 × 选题修正，输出区间+置信度 |
| L2+ 受众层 | 7 类读者原型（年龄+行业+阅读性格）启发式共鸣模拟，指出打动谁、谁无感、怎么撬动 |
| L3 合规层 | 微信官方9条红线逐条检查（依据 references/platform-rules*.md），输出 通过/修改后发布 判定 |
| L4 反AI层 | AI写作痕迹扫描（排比三连/AI高频词/空洞修饰/破折号滥用/套路开头/升华结尾等） |

## 全行业多赛道

检测引擎内置 11 个赛道词库（科技AI / 财经投资 / 职场成长 / 健康养生 / 教育育儿 / 婚恋情感 / 美食生活 / 美妆时尚 / 房产楼市 / 中老年情感 / 通用情感），自动识别赛道后差异化计分与预测。`赛道` 决定"写给谁"，`风格` 决定"怎么写"，二者正交——绝不用一套"干货文尺子"去错杀情绪随笔。

## 安装

```bash
# 方式一：复制整个目录到 skills 目录（Claude Code / WorkBuddy / OpenClaw）
cp -r wechat-hit-detector-skill ~/.workbuddy/skills/

# 方式二：通过 skills 市场安装（若已发布）
npx skills add Gelen5/wechat-hit-detector-skill
```

或通过 skills.json 引用本仓库 URL。

## 使用

对话中直接说：

```
帮我检测这篇文章 https://mp.weixin.qq.com/s/xxx
或：帮我检测这篇稿子（粘贴标题+正文）
```

命令行直接跑：

```bash
# 抓取公众号文章
python3 scripts/fetch_article.py "https://mp.weixin.qq.com/s/xxx" -o article.md

# 检测（可附粉丝数和账号打开率，提升预测置信度）
python3 scripts/detector.py "文章标题" article.md --fans 82000 --open-rate 9.2

# 强制指定赛道（覆盖自动识别，用于跨赛道对比）
python3 scripts/detector.py "文章标题" article.md --track workplace
```

## 目录结构

```
wechat-hit-detector-skill/
├── SKILL.md                  # 技能定义（触发词/流程/评分规则/输出模板）
├── scripts/
│   ├── detector.py           # 四层检测引擎（含风格自适应 + 受众模拟 + HTML报告）
│   └── fetch_article.py      # 公众号链接抓取器
├── references/
│   ├── platform-rules.md     # 微信推荐运营规范9条红线（官方原文）
│   └── platform-rules-basic.md  # 基础运营规范补充条款
└── examples/                 # 示例文章（多赛道 + 私人测试稿）
```

## 输出

- 综合评分 + 等级（S/A/B/C，附发布建议）
- 阅读量预测区间 + 预测打开率 + 置信度
- 六维评分明细（按风格适配，含得分点）
- 7 类受众共鸣画像（启发式模拟，非真实数据）
- 9条红线合规结果
- 反AI味扫描结果
- 本篇亮点高亮
- 按优先级排序的改稿清单（P0半小时可改 / P1半天 / P2长期）
- 自动生成 `report.html`（苹果级暗色磨砂玻璃可视化报告，含 hero 大字号、入场动效、一键复制改稿清单）

## 边界

- 阅读量为预测区间，非真实值（真实值仅号主后台可见）
- 受众共鸣为本地启发式模拟，非真实阅读数据
- 合规报告为参考，非平台最终判决
- 已删除文章无法抓取，防爬失败时请手动粘贴标题+正文
