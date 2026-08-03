# wechat-hit-detector-skill 公众号爆款检测

微信公众号文章**发布前**爆款检测 Skill。四层检测引擎：内容六维评分 + 阅读量预测 + 微信9条红线合规 + 反AI味扫描，一条命令输出可执行改稿清单。

## 功能

| 层 | 能力 |
|---|---|
| L1 内容层 | 六维评分（标题钩子力25 / 开头留住力20 / 内容价值度20 / 选题势能15 / 中老年可读性10 / 互动转化10） |
| L2 数据层 | 阅读量预测：粉丝数 × 账号基准打开率 × 标题修正 × 选题修正，输出区间+置信度 |
| L3 合规层 | 微信官方9条红线逐条检查（依据 references/platform-rules*.md），输出 通过x/9 + 可发布判断 |
| L4 反AI层 | AI写作痕迹扫描（排比三连/AI高频词/空洞修饰/破折号滥用/套路开头/升华结尾等8类模式） |

适配赛道：中老年情感 / 早安文案 / 养老金政策（词库已含通用情感词，其他情感号可用）。

## 安装

```bash
# 方式一：复制整个目录到 skills 目录（Claude Code / WorkBuddy / OpenClaw）
cp -r wechat-hit-detector-skill ~/.claude/skills/

# 方式二：npm 安装（若已发布到 skills.sh）
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
```

## 目录结构

```
wechat-hit-detector-skill/
├── SKILL.md                  # 技能定义（触发词/流程/评分规则/输出模板）
├── scripts/
│   ├── detector.py           # 四层检测引擎
│   └── fetch_article.py      # 公众号链接抓取器
├── references/
│   ├── platform-rules.md     # 微信推荐运营规范9条红线（官方原文）
│   └── platform-rules-basic.md  # 基础运营规范补充条款
└── examples/                 # 示例文章
```

## 输出

- 综合评分 + 等级（S/A/B/C，附发布建议）
- 阅读量预测区间 + 预测打开率 + 置信度
- 六维评分明细（含得分点）
- 9条红线合规结果
- 反AI味扫描结果
- 按优先级排序的改稿清单（P0半小时可改 / P1半天 / P2长期）

同时自动生成 `report.html`（暗色 IKB 蓝可视化报告），浏览器直接打开。

## 边界

- 阅读量为预测区间，非真实值（真实值仅号主后台可见）
- 合规报告为参考，非平台最终判决
- 已删除文章无法抓取，防爬失败时请手动粘贴标题+正文
