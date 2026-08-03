#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章发布前爆款检测引擎 v1.0
================================
四层检测：L1 内容六维评分 / L2 阅读量预测 / L3 9条红线合规 / L4 反AI味检测

用法:
    python3 detector.py <标题> <正文文件路径> [--fans 粉丝数] [--open-rate 账号基准打开率%]

示例:
    python3 detector.py "退休第2年，老伴开始嫌弃我了" article.md
    python3 detector.py "退休第2年，老伴开始嫌弃我了" article.md --fans 82000 --open-rate 9.2

输出:
    终端 Markdown 报告 + 同目录 report.html（暗色IKB蓝可视化）
"""

import re
import sys
import json
import argparse
import datetime

# ============================================================
# 赛道词库（中老年情感 / 养老金 / 早安文案 校准）
# ============================================================
GROUP_WORDS = ["退休", "老伴", "中老年", "爸妈", "父母", "母亲", "父亲", "大爷", "大妈",
               "60岁", "50岁", "70岁", "老年", "养老", "黄昏恋", "子女", "孙辈", "孙子", "孙女",
               "结婚", "夫妻", "婚姻", "恋爱", "老公", "老婆", "孩子", "家庭", "中年",
               "已婚", "未婚", "离婚", "家", "女儿", "儿子"]
PAIN_WORDS = ["越来越少", "没话说", "变淡", "陌生", "沉默", "冷战", "吵架", "渐行渐远",
              "没意思", "不如从前", "不爱", "变了", "隔阂", "疏远", "累"]
BENEFIT_WORDS = ["养老金", "退休金", "补贴", "医保", "涨", "领钱", "补发", "报销", "省钱",
                 "待遇", "福利", "新政", "调整", "通知", "2026", "新规"]
EMOTION_CONFLICT = ["嫌弃", "离婚", "藏", "哭", "吵", "逼", "求", "骗", "离开", "背叛",
                    "心寒", "委屈", "寒心", "分房", "争", "闹", "打", "扔", "砸", "跪",
                    "走了", "住院", "手术", "摔", "失踪", "查"]
SUSPENSE_WORDS = ["竟然", "悄悄", "为什么", "终于", "没想到", "藏着", "背后的", "真相",
                  "秘密", "后悔", "一夜之间", "突然", "到底", "究竟是"]
AI_OPENING = ["在当今", "随着", "众所周知", "今天我们来聊聊", "在如今", "随着社会",
              "在现在这个", "首先", "综上所述", "总而言之", "值得注意的是"]
AI_WORDS = ["赋能", "格局", "认知升级", "干货满满", "满满的干货", "优质内容", "深度好文",
            "助力", "打造", "闭环", "底层逻辑", "思维模型", "抓手", "颗粒度", "组合拳",
            "拥抱变化", "破圈", "红利", "赛道", "精细化运营", "此外", "值得注意的是",
            "不可否认", "毋庸置疑", "由此可见"]
EMPTY_MODIFIERS = ["仿佛", "宛如", "仿佛置身", "仿佛让人", "令人心旷神怡", "岁月静好",
                   "微风拂面", "流光溢彩", "熠熠生辉", "如诗如画"]
HEALTH_RISK = ["偏方", "秘方", "治百病", "根治", "包治", "排毒", "抗癌", "降三高立竿见影",
               "食疗治", "药到病除", "养生神方"]
CLICKBAIT = ["震惊", "速看", "删前速看", "惊天", "吓人", "千万别", "转疯了", "必转",
             "不转不是", "马上删", "疯了", "重磅", "紧急通知"]
SUPERSTITION = ["属相", "风水", "算命", "大师", "开运", "转运", "犯太岁", "推背图",
                "前世", "因果报应", "附体"]
INDUCE = ["转发后领取", "分享截图", "关注后领取", "扫码关注", "不转不是", "转发一生平安",
          "点赞抽奖", "集赞", "邀请好友", "助力"]
TRIPLE_PATTERN = re.compile(r"[^，。；\n]*[，、][^，。；\n]*[，、][^，。；\n]*")
LEVELS = {"S": (85, "爆款潜力，直接发"), "A": (70, "改完 P0 项后发"),
          "B": (55, "大改标题+开头再考虑"), "C": (0, "选题建议重做")}

# ============================================================
# L1-1 标题钩子力 (25)
# ============================================================
def score_title(title):
    b = []
    s = 0
    if re.search(r"\d|第[一二三四五六七八九十\d]+年|\d+岁", title):
        s += 5; b.append(("含具体数字/时间锚点", 5))
    if any(w in title for w in GROUP_WORDS):
        s += 5; b.append(("命中特定群体（退休/老伴等）", 5))
    if any(w in title for w in EMOTION_CONFLICT):
        s += 6; b.append(("含情绪冲突/反转词", 6))
    elif any(w in title for w in SUSPENSE_WORDS):
        s += 4; b.append(("含悬念词", 4))
    if any(w in title for w in SUSPENSE_WORDS):
        s += 4; b.append(("含悬念缺口（竟然/悄悄/为什么）", 4))
    if any(w in title for w in PAIN_WORDS):
        s += 4; b.append(("痛点共鸣（话少/变淡/累等普遍情绪）", 4))
    if any(w in title for w in BENEFIT_WORDS):
        s += 1; b.append(("含利益点（钱/政策）", 1))
    n = len(title)
    if 15 <= n <= 25:
        s += 4; b.append((f"字数{n}，处于最优区间15-25字", 4))
    elif 10 <= n <= 30:
        s += 2; b.append((f"字数{n}，可接受区间", 2))
    else:
        b.append((f"字数{n}，偏离最优区间", 0))
    s = min(s, 25)
    return s, b

# ============================================================
# L1-2 开头留住力 (20)
# ============================================================
def score_opening(body):
    b = []
    s = 0
    head = re.sub(r"\s+", "", body)[:100]
    if re.search(r"\d|今年|去年|那天|那天晚上|清晨|半夜|退休后|刚退休", head):
        s += 6; b.append(("开头有具体时间/场景锚点", 6))
    if "“" in head or '"' in head or "说" in head or "喊" in head or "问" in head:
        s += 5; b.append(("开头有对话/人物动作", 5))
    if not any(w in head for w in AI_OPENING):
        s += 4; b.append(("开头无AI套路开场白", 4))
    else:
        for w in AI_OPENING:
            if w in head:
                b.append((f"警告:开头含AI套路词「{w}」", 0)); break
    if any(w in head for w in EMOTION_CONFLICT + SUSPENSE_WORDS):
        s += 3; b.append(("开头即入冲突/悬念", 3))
    if avg_sentence_len(head) <= 25:
        s += 2; b.append(("开头句子短促，利于扫读", 2))
    return min(s, 20), b

# ============================================================
# L1-3 内容价值度 (20)
# ============================================================
def score_content(body):
    b = []
    s = 0
    paras = [p for p in body.split("\n") if p.strip()]
    sentences = [x for x in re.split(r"[。！？!?]", body) if x.strip()]
    total_chars = len(re.sub(r"\s+", "", body))
    # 结构：分段数
    if len(paras) >= 5:
        s += 4; b.append(("分段合理（≥5段）", 4))
    elif len(paras) >= 3:
        s += 2; b.append(("分段一般（3-4段）", 2))
    else:
        b.append((f"仅{len(paras)}段，长文块劝退", 0))
    # 段落长度
    long_paras = [p for p in paras if len(p) > 180]
    if not long_paras:
        s += 4; b.append(("无超长段落", 4))
    else:
        b.append((f"{len(long_paras)}个段落超长（>180字），建议拆分", 0))
    # 情绪浓度
    emotion_hits = sum(1 for w in ["哭", "笑", "心酸", "委屈", "温暖", "幸福", "难受",
                                   "心疼", "心软", "泪", "暖", "甜", "苦", "恨", "爱",
                                   "懵", "抖", "愣", "红", "气", "怕", "扛", "盼",
                                   "念", "踏实", "慌", "凉", "急"] for w in re.findall(w, body))
    rate = emotion_hits * 1000 / max(total_chars, 1)
    if rate >= 4:
        s += 4; b.append((f"情绪词密度{rate:.1f}/千字，浓度足", 4))
    elif rate >= 2:
        s += 2; b.append((f"情绪词密度{rate:.1f}/千字，一般", 2))
    else:
        b.append((f"情绪词密度{rate:.1f}/千字，偏干", 0))
    # 细节真实性
    if re.search(r"\d+(万|元|块|岁|年|天|点)|“[^”]{4,}”", body):
        s += 4; b.append(("含具体数字/真实对话细节", 4))
    # 结尾收束
    tail = body[-150:]
    if re.search(r"其实|说到底|想通|明白了|原来|过日子|这辈子", tail):
        s += 4; b.append(("结尾有情绪收束/点题", 4))
    else:
        b.append(("结尾缺少点题收束", 0))
    return min(s, 20), b

# ============================================================
# L1-4 选题势能 (15)
# ============================================================
def score_topic(title, body):
    b = []
    s = 0
    text = title + body
    group_hits = [w for w in GROUP_WORDS if w in text]
    benefit_hits = [w for w in BENEFIT_WORDS if w in text]
    if group_hits:
        s += 6; b.append((f"命中赛道高频词：{'、'.join(list(set(group_hits))[:4])}", 6))
    else:
        b.append(("未命中赛道高频词", 0))
    if any(w in text for w in PAIN_WORDS):
        s += 3; b.append(("含普遍情绪痛点（共鸣面广）", 3))
    if benefit_hits:
        s += 3; b.append(("含利益/政策点（钱、补贴、新政）", 3))
    if any(w in text for w in ["新政", "调整", "通知", "2026", "新规", "最新"]):
        s += 3; b.append(("有时效/政策热点", 3))
    # 同质化警示（无外部数据时的启发式）
    if re.search(r"退休.*(老伴|嫌弃|离婚|分房|吵)", title) and len(benefit_hits) == 0:
        s -= 2; b.append(("⚠ 同质化预警：'退休+情感冲突'套路常见，建议叠加利益/政策角度做差异化", -2))
    return max(min(s, 15), 0), b

# ============================================================
# L1-5 中老年可读性 (10)
# ============================================================
def avg_sentence_len(text):
    ss = [x for x in re.split(r"[。！？!?；;，,]", text) if x.strip()]
    if not ss:
        return 99
    return sum(len(x) for x in ss) / len(ss)

def score_readability(body):
    b = []
    s = 0
    al = avg_sentence_len(body)
    if al <= 25:
        s += 4; b.append((f"平均句长{al:.0f}字，适合中老年阅读", 4))
    elif al <= 35:
        s += 2; b.append((f"平均句长{al:.0f}字，建议拆短", 2))
    else:
        b.append((f"平均句长{al:.0f}字，过长", 0))
    if not re.search(r"[A-Za-z]{2,}", body):
        s += 2; b.append(("无英文缩写/夹生词", 2))
    paras = [p for p in body.split("\n") if p.strip()]
    if all(len(p) <= 120 for p in paras):
        s += 2; b.append(("段落规整（≤120字/段）", 2))
    b.append(("排版提示：正文建议字号≥18px、行距1.75", 0))
    return min(s + 2, 10), b

# ============================================================
# L1-6 互动转化 (10)
# ============================================================
def score_interaction(body):
    b = []
    s = 0
    tail = body[-200:]
    if re.search(r"[？?].{0,20}？|你们|你家里|你家|评论区|留言", tail):
        s += 4; b.append(("结尾有提问互动", 4))
    else:
        b.append(("结尾无提问，读完即走", 0))
    if re.search(r"在看|点个赞|点赞|转发|分享给|发给", body):
        s += 3; b.append(("有在看/点赞引导", 3))
    if re.search(r"评论区|留言|说说你|你的看法|聊聊", body):
        s += 3; b.append(("有评论区话题设计", 3))
    return min(s, 10), b

# ============================================================
# L3 合规检查（基于 references/platform-rules*.md）
# ============================================================
def compliance_check(title, body):
    findings = []
    text = title + body
    if re.search(r"养老金|退休金|医保|补贴|新政|新规|调整", text) and not re.search(r"来源[:：]|据.*报道|据.*发布|官网|官方|记者", text):
        findings.append(("红线8·过时信息", "政策/待遇内容未标注信息来源与生效时间，政策号最大雷区：条款修订后旧文会被判低质", "修改后发布"))
    if [w for w in HEALTH_RISK if w in text]:
        findings.append(("红线5.1·不规范医疗科普", f"命中夸大医疗表述：{'、'.join([w for w in HEALTH_RISK if w in text][:3])}。需标注'不替代专业诊断'", "修改后发布"))
    if [w for w in INDUCE if w in text]:
        findings.append(("基础3.3·诱导行为", f"命中诱导词：{'、'.join([w for w in INDUCE if w in text][:3])}。诱导分享/关注违规", "修改后发布"))
    if [w for w in CLICKBAIT if w in title]:
        findings.append(("红线5.3.3·误导标题", f"标题命中标题党词：{'、'.join([w for w in CLICKBAIT if w in title][:3])}。浮夸煽动", "修改后发布"))
    if [w for w in SUPERSTITION if w in text]:
        findings.append(("红线5.2·封建迷信", f"命中迷信词：{'、'.join([w for w in SUPERSTITION if w in text][:3])}。需标注'仅供阅读参考'", "修改后发布"))
    if re.search(r"刷屏|必转|疯传|火遍全网", text):
        findings.append(("红线7·低创作度", "命中营销传播词，注意避免夸大转发效果", "提示"))
    return findings

# ============================================================
# L4 反AI味检测（humanizer 24类模式 + 公众号指纹）
# ============================================================
def ai_smell_check(body):
    findings = []
    text = body
    # 1. 三连排比
    for m in re.finditer(r"[^。\n]{15,40}[，、][^。\n]{15,40}[，、][^。\n]{15,40}[。！]", text):
        findings.append(("排比三连", f"疑似工整排比：{m.group(0)[:40]}…", "建议打散节奏，一句说一件事"))
        break
    # 2. AI高频词
    hits = [w for w in AI_WORDS if w in text]
    if hits:
        findings.append(("AI高频词", f"命中：{'、'.join(hits[:5])}", "替换为口语化表达"))
    # 3. 空洞修饰
    hits2 = [w for w in EMPTY_MODIFIERS if w in text]
    if hits2:
        findings.append(("空洞修饰", f"命中：{'、'.join(hits2[:3])}", "换成具体细节"))
    # 4. 破折号滥用
    if text.count("——") >= 3:
        findings.append(("破折号滥用", f"全文{text.count('——')}处'——'，AI常见标点习惯", "改为逗号或句号"))
    # 5. 空洞开头
    for w in AI_OPENING:
        if w in text[:60]:
            findings.append(("AI套路开头", f"开头命中「{w}」模板", "直接进入场景/冲突"))
            break
    # 6. 结尾升华模板
    if re.search(r"愿我们|让我们.*吧|希望我们|愿天下|谨以此文", text[-200:]):
        findings.append(("结尾升华模板", "结尾'愿我们…'式升华是AI标志", "用具体故事收尾"))
    # 7. 无个人细节（整文无对话无数字）
    if not re.search(r"“|”|说|喊|\d", text):
        findings.append(("细节缺失", "全文无对话/无数字，读感悬浮", "补具体场景与真实细节"))
    # 8. 同质化句式
    if text.count("不是…而是…") or len(re.findall(r"不仅是.{0,20}更是", text)) >= 1:
        findings.append(("否定并列句式", "'不是…而是…'式句式AI高频", "直接陈述"))
    return findings

# ============================================================
# L2 阅读量预测
# ============================================================
def predict_reads(title_score, topic_score, fans=None, base_open_rate=None):
    base = base_open_rate if base_open_rate else 6.0  # 赛道默认基准
    title_k = 0.6 + (title_score / 25) * 1.2          # 0.6 ~ 1.8
    topic_k = 0.8 + (topic_score / 15) * 0.7          # 0.8 ~ 1.5
    open_rate = min(base * title_k * topic_k, 25.0)
    if not fans:
        return None, open_rate, title_k, topic_k, "低（无账号基准，需粉丝数+历史数据）"
    lo = int(fans * open_rate / 100 * 0.7)
    hi = int(fans * open_rate / 100 * 1.3)
    conf = "高" if base_open_rate else "中"
    return (lo, hi), open_rate, title_k, topic_k, conf

# ============================================================
# 报告生成
# ============================================================
def detect(title, body, fans=None, base_open_rate=None):
    t_s, t_b = score_title(title)
    o_s, o_b = score_opening(body)
    c_s, c_b = score_content(body)
    tp_s, tp_b = score_topic(title, body)
    r_s, r_b = score_readability(body)
    i_s, i_b = score_interaction(body)
    total = t_s + o_s + c_s + tp_s + r_s + i_s
    for name, th in [("S", 85), ("A", 70), ("B", 55)]:
        if total >= th:
            level, lvl_desc = name, LEVELS[name][1]
            break
    else:
        level, lvl_desc = "C", LEVELS["C"][1]
    compliance = compliance_check(title, body)
    ai = ai_smell_check(body)
    reads = predict_reads(t_s, tp_s, fans, base_open_rate)
    # 改稿建议（按成本×收益排序）
    adv = []
    if t_s < 16:
        adv.append(("P0", "标题钩子不足", f"({t_s}/25) 套用标题公式重写：具体数字+特定群体+情绪反转，例：'退休第2年，老伴把离婚协议藏进了衣柜'"))
    if o_s < 12:
        adv.append(("P0", "开头没留住人", f"({o_s}/20) 砍掉铺垫直接入戏：时间/地点/对话开场，第一时间抛冲突"))
    if i_s < 6:
        adv.append(("P0", "结尾零互动", f"({i_s}/10) 留白后补提问：'你家呢？评论区说说你的看法'"))
    if c_s < 12:
        adv.append(("P1", "内容价值偏薄", f"({c_s}/20) 补具体数字/真实对话/金句，加小标题拆分长段落"))
    if tp_s < 9:
        adv.append(("P1", "选题势能偏弱", f"({tp_s}/15) 叠加利益/政策角度（养老金/补贴/新政），或转蓝海细分"))
    if ai:
        adv.append(("P1", "AI味检测", f"{len(ai)}处，改完过一遍反AI流程（humanizer）再发布"))
    for tag, msg, act in compliance:
        adv.append(("P1", "合规整改", f"[{tag}] {act}"))
    if not adv:
        adv.append(("P2", "整体达标", "发布前：固定早6:30-7:00推送，配图统一IKB蓝风格"))
    return {
        "title": title, "fans": fans, "base_open_rate": base_open_rate,
        "total": total, "level": level, "level_desc": lvl_desc,
        "dims": [("标题钩子力", t_s, 25, t_b), ("开头留住力", o_s, 20, o_b),
                 ("内容价值度", c_s, 20, c_b), ("选题势能", tp_s, 15, tp_b),
                 ("中老年可读性", r_s, 10, r_b), ("互动转化", i_s, 10, i_b)],
        "compliance": compliance, "ai": ai, "reads": reads, "adv": adv,
    }

def fmt_md(r):
    L = []
    L.append(f"## 爆款检测报告")
    L.append(f"**文章**：{r['title']}")
    L.append(f"**综合评分**：{r['total']}/100 · **{r['level']}级** · {r['level_desc']}")
    L.append("")
    L.append("### 六维评分")
    for name, s, full, _ in r["dims"]:
        bar = "█" * round(s / full * 12)
        L.append(f"- {name} {s}/{full} {bar}")
    L.append("")
    if r["reads"][0]:
        lo, hi = r["reads"][0]
        L.append(f"### 阅读量预测：{lo:,} ~ {hi:,}")
    else:
        L.append("### 阅读量预测：需提供粉丝数（当前按'每1万粉丝'基准）")
    L.append(f"- 预测打开率 {r['reads'][1]:.1f}%（标题修正×{r['reads'][2]:.2f}，选题修正×{r['reads'][3]:.2f}）")
    L.append(f"- 置信度：{r['reads'][4]}")
    L.append("")
    L.append("### 合规检查")
    if r["compliance"]:
        for tag, msg, act in r["compliance"]:
            L.append(f"- [{tag}] {msg} → **{act}**")
    else:
        L.append("- 未命中明显违规，可通过")
    L.append("")
    L.append("### 反AI味扫描")
    if r["ai"]:
        for pat, loc, fix in r["ai"]:
            L.append(f"- [{pat}] {loc} → {fix}")
    else:
        L.append("- 未见明显AI痕迹")
    L.append("")
    L.append("### 改稿建议（按优先级）")
    if r["adv"]:
        for pri, tag, detail in r["adv"]:
            L.append(f"- **{pri}** {tag}：{detail}")
    else:
        L.append("- 整体达标，可直接发布")
    return "\n".join(L)

def fmt_html(r):
    dims_html = ""
    for name, s, full, _ in r["dims"]:
        pct = s / full * 100
        color = "#3ddc97" if pct >= 75 else ("#ffb020" if pct >= 55 else "#ff5d5d")
        dims_html += f"""<div style="margin-bottom:10px"><div style="display:flex;justify-content:space-between;font-size:13px;color:#9b9bb2;margin-bottom:4px"><span>{name}</span><span><b style="color:#e9e9f2">{s}</b>/{full}</span></div><div style="height:6px;background:rgba(255,255,255,.08);border-radius:99px;overflow:hidden"><div style="width:{pct}%;height:100%;background:linear-gradient(90deg,#002FA7,{color});border-radius:99px"></div></div></div>"""
    comp_html = "".join(f'<div style="padding:8px 0;border-bottom:1px dashed rgba(255,255,255,.08);font-size:12.5px;color:#9b9bb2"><b style="color:#ff5d5d">[{tag}]</b> {msg} <b style="color:#ffb020">→ {act}</b></div>' for tag, msg, act in r["compliance"]) or '<div style="font-size:12.5px;color:#3ddc97">未命中明显违规，可通过</div>'
    ai_html = "".join(f'<div style="padding:8px 0;border-bottom:1px dashed rgba(255,255,255,.08);font-size:12.5px;color:#9b9bb2"><b style="color:#ffb020">[{pat}]</b> {loc} → <span style="color:#a9c0ff">{fix}</span></div>' for pat, loc, fix in r["ai"]) or '<div style="font-size:12.5px;color:#3ddc97">未见明显AI痕迹</div>'
    adv_html = "".join(f'<div style="padding:9px 0;border-bottom:1px dashed rgba(255,255,255,.08)"><span style="display:inline-block;font-size:11px;font-weight:800;color:#fff;background:#002FA7;padding:2px 9px;border-radius:7px;margin-right:8px">{pri}</span><b style="font-size:13px">{tag}</b><div style="font-size:12px;color:#9b9bb2;margin-top:3px">{detail}</div></div>' for pri, tag, detail in r["adv"])
    if r["reads"][0]:
        reads_html = f'<div style="font-size:34px;font-weight:800;background:linear-gradient(90deg,#fff,#1d4ed8);-webkit-background-clip:text;background-clip:text;color:transparent">{r["reads"][0][0]:,} ~ {r["reads"][0][1]:,}</div>'
    else:
        reads_html = '<div style="font-size:24px;font-weight:800;color:#9b9bb2">需提供粉丝数</div>'
    lvl_color = "#3ddc97" if r["level"] == "S" or r["level"] == "A" else ("#ffb020" if r["level"] == "B" else "#ff5d5d")
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>爆款检测报告</title></head>
<body style="margin:0;background:#0b0b10;color:#e9e9f2;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif">
<div style="max-width:920px;margin:0 auto;padding:32px 20px 64px">
<div style="font-size:11px;color:#a9c0ff;border:1px solid rgba(0,47,167,.5);background:rgba(0,47,167,.15);padding:4px 12px;border-radius:99px;display:inline-block;letter-spacing:1px">发布前爆款检测 · {datetime.date.today()}</div>
<h1 style="font-size:24px;margin:14px 0 6px">{r["title"]}</h1>
<div style="font-size:13px;color:#9b9bb2;margin-bottom:22px">综合评分 <b style="color:#e9e9f2">{r["total"]}</b>/100 · <b style="color:{lvl_color}">{r["level"]}级</b> · {r["level_desc"]}</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px">
<div style="background:#14141d;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:18px"><div style="font-size:11px;color:#9b9bb2;letter-spacing:1px">阅读量预测区间</div>{reads_html}<div style="font-size:12px;color:#9b9bb2;margin-top:6px">打开率 {r["reads"][1]:.1f}% · 修正 ×{r["reads"][2]:.2f} ×{r["reads"][3]:.2f} · 置信度 {r["reads"][4]}</div></div>
<div style="background:#14141d;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:18px"><div style="font-size:11px;color:#9b9bb2;letter-spacing:1px;margin-bottom:10px">六维评分</div>{dims_html}</div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px">
<div style="background:#14141d;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:18px"><div style="font-size:13px;font-weight:700;margin-bottom:8px">合规检查</div>{comp_html}</div>
<div style="background:#14141d;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:18px"><div style="font-size:13px;font-weight:700;margin-bottom:8px">反AI味扫描</div>{ai_html}</div>
</div>
<div style="background:#14141d;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:18px"><div style="font-size:13px;font-weight:700;margin-bottom:4px">改稿建议（按优先级）</div>{adv_html}</div>
</div></body></html>"""

def main():
    ap = argparse.ArgumentParser(description="公众号发布前爆款检测引擎")
    ap.add_argument("title", help="文章标题")
    ap.add_argument("body_file", help="正文文件路径")
    ap.add_argument("--fans", type=int, default=None, help="粉丝数")
    ap.add_argument("--open-rate", type=float, default=None, help="账号基准打开率(%)")
    args = ap.parse_args()
    with open(args.body_file, encoding="utf-8") as f:
        body = f.read()
    report = detect(args.title, body, args.fans, args.open_rate)
    print(fmt_md(report))
    with open("report.html", "w", encoding="utf-8") as f:
        f.write(fmt_html(report))
    print("\n[已生成可视化报告 report.html]")

if __name__ == "__main__":
    main()
