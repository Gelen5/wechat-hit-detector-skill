import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import detector  # noqa: E402
import compare_versions  # noqa: E402


class DetectorRegressionTests(unittest.TestCase):
    def test_single_character_superlative_is_not_a_false_positive(self):
        issues = detector.compliance_check(
            "这是我见过最普通的一天",
            "今天下班回家，买了菜，吃完饭后看了一会儿书。",
            "general",
        )
        self.assertFalse(any(i["line"] == "绝对化宣传表述（需结合语境）" for i in issues))

    def test_ordinary_first_year_and_negated_ranking_are_not_ad_claims(self):
        issues = detector.compliance_check(
            "退休第一年，我学会了慢旅行",
            "退休第一年，我去了洛阳。这里不是全国第一，只是我个人喜欢。",
            "senior",
        )
        self.assertFalse(any(i["line"] == "绝对化宣传表述（需结合语境）" for i in issues))

    def test_promotional_ranking_remains_a_contextual_review_hit(self):
        issues = detector.compliance_check(
            "销量第一的课程",
            "这是行业第一的课程，保证效果。",
            "education",
        )
        self.assertTrue(any(i["line"] == "绝对化宣传表述（需结合语境）" for i in issues))

    def test_spacing_variant_of_inducement_is_detected(self):
        issues = detector.compliance_check(
            "福利通知",
            "转 发 后 领 取资料，关注后领取。",
            "general",
        )
        self.assertTrue(any("诱导分享/关注" == i["line"] for i in issues))

    def test_negated_medical_claim_is_not_treated_as_a_claim(self):
        issues = detector.compliance_check(
            "健康科普",
            "目前没有可靠证据证明这种方法可以治疗失眠。",
            "health",
        )
        self.assertFalse(any("医疗功效表述" in i["line"] for i in issues))

    def test_positive_medical_claim_remains_a_review_hit(self):
        issues = detector.compliance_check(
            "健康方法",
            "这种方法可以治疗失眠。",
            "health",
        )
        self.assertTrue(any("医疗功效表述" in i["line"] for i in issues))

    def test_missing_fans_does_not_invent_read_count(self):
        result = detector.detect("普通的一天", "今天下班后回家，安静地吃了晚饭。", fans=None)
        self.assertIsNone(result["predict"]["predict"])
        self.assertIsNone(result["predict"]["baseline_reads"])
        self.assertEqual(result["predict"]["confidence"], "not_estimated")
        self.assertEqual(result["predict"]["scenario_reads"], [])
        self.assertIsNone(result["predict"]["eff_open_rate"])

    def test_account_baseline_never_becomes_article_prediction(self):
        result = detector.detect(
            "普通的一天",
            "今天下班后回家，安静地吃了晚饭。",
            fans=10000,
            open_rate=5.0,
        )
        self.assertEqual(result["predict"]["baseline_reads"], 500)
        self.assertIsNone(result["predict"]["predict"])
        self.assertEqual(result["predict"]["data_state"], "account_baseline")

    def test_oral_signal_is_positive_not_template_risk(self):
        _, risk, findings = detector.ai_smell_check(
            "我们都在等对方先开口",
            "我妈问我最近怎么样，我说还行。其实我一点也不好。",
        )
        self.assertEqual(risk, 0)
        self.assertTrue(any(f.startswith("✅ 自然表达加分") for f in findings))

    def test_finance_disclaimer_check_is_conditional(self):
        clean = detector.compliance_check("利率变化", "本文整理公开数据。", "finance")
        risky = detector.compliance_check("买入建议", "我给出明确的投资建议。", "finance")
        self.assertFalse(any("金融误导风险" in i["line"] for i in clean))
        self.assertTrue(any("金融误导风险" in i["line"] for i in risky))

    def test_evidence_review_surfaces_policy_freshness(self):
        issues = detector.evidence_review("养老金新规", "养老金待遇将发生变化。", "senior", "news")
        kinds = {i["type"] for i in issues}
        self.assertIn("source", kinds)
        self.assertIn("freshness", kinds)

    def test_authority_claim_enters_source_ledger_as_blocker(self):
        result = detector.detect(
            "适合退休旅行的小城",
            "联合国评定这里是宜居城市。",
            track="senior",
        )
        self.assertTrue(any(i["claim_type"] == "authority" for i in result["source_ledger"]))
        self.assertEqual(result["editorial_gate"]["status"], "hold")

    def test_place_name_with_country_word_is_not_authority_claim(self):
        ledger = detector.build_source_ledger(
            "去国家公园散步",
            "周末我去国家公园走了一圈。",
            "general",
            "narrative",
        )
        self.assertFalse(any(i["claim_type"] == "authority" for i in ledger))

    def test_first_person_experience_requires_confirmation_not_fake_proof(self):
        result = detector.detect(
            "退休旅行避坑",
            "我身边一半朋友都中过这个坑，我自己也踩过。",
            track="senior",
        )
        self.assertTrue(any(i["claim_type"] == "experience" for i in result["source_ledger"]))
        self.assertIn("第一人称经历需要作者确认", result["editorial_gate"]["confirmations"])

    def test_unfulfilled_clickbait_is_blocked_and_not_rewarded_over_clear_title(self):
        body = """退休后可以挑个周二去小城慢慢住。
① 洛阳
适合慢慢逛。
② 扬州
老城区路平。
③ 威海
适合看海。
④ 建水
可以坐小火车。
⑤ 衢州
适合慢走。
⑥ 高邮
老街很安静。"""
        clear = detector.detect("退休后适合慢慢住的6座小城", body, track="senior")
        clickbait = detector.detect("60岁后一定要去的6座小城：第4个我后悔现在才知道", body, track="senior")
        self.assertGreaterEqual(clear["scores"]["title"], clickbait["scores"]["title"])
        self.assertNotEqual(clear["editorial_gate"]["status"], "hold")
        self.assertEqual(clickbait["editorial_gate"]["status"], "hold")
        self.assertTrue(any(i["title"] == "标题悬念在正文中没有兑现" for i in clickbait["evidence"]))

    def test_arabic_title_number_can_be_supported_by_chinese_body_number(self):
        issues = detector.evidence_review(
            "一碗面5块钱",
            "老街上的一碗阳春面五块钱。",
            "food",
            "practical",
        )
        self.assertFalse(any(i["title"] == "标题数字承诺未被正文承接" for i in issues))

    def test_revision_comparison_proves_resolved_and_new_issues(self):
        before = detector.detect(
            "60岁后去这6座小城：第4个我后悔现在才知道",
            "① 洛阳\n② 扬州\n③ 威海\n④ 建水\n⑤ 衢州\n⑥ 高邮",
            track="senior",
        )
        after = detector.detect(
            "退休后适合慢慢住的6座小城",
            "① 洛阳\n② 扬州\n③ 威海\n④ 建水\n⑤ 衢州\n⑥ 高邮",
            track="senior",
        )
        comparison = compare_versions.compare_results(before, after)
        self.assertTrue(any(i["title"] == "标题悬念在正文中没有兑现" for i in comparison["resolved"]))
        self.assertFalse(any(i["title"] == "标题悬念在正文中没有兑现" for i in comparison["remaining"]))

    def test_content_risk_splits_machine_and_substantive_signals(self):
        result = detector.content_risk_review(
            "福利通知",
            "想了解课程报价可以加微信下单，限时优惠。",
            "education",
        )
        self.assertTrue(any("联系方式" in i["signal"] for i in result["machine"]))
        self.assertTrue(any("交易动作" in i["signal"] for i in result["substantive"]))

    def test_platform_name_alone_is_not_substantive_risk(self):
        result = detector.content_risk_review(
            "我在闲鱼买到一本旧书",
            "这只是一次普通的二手书购买经历，没有联系方式，也没有导流。",
            "general",
        )
        self.assertTrue(any("平台/圈层词" in i["signal"] for i in result["machine"]))
        self.assertFalse(result["substantive"])

    def test_medical_promise_is_substantive_risk(self):
        result = detector.content_risk_review(
            "这个方法治愈失眠",
            "这个方法一定有效，能治疗失眠，立刻见效。",
            "health",
        )
        self.assertTrue(any("健康/疗效承诺" in i["signal"] for i in result["substantive"]))

    def test_detect_returns_content_risk_layer(self):
        result = detector.detect("普通的一天", "今天下班后回家，安静地吃了晚饭。")
        self.assertIn("content_risk", result)
        self.assertEqual(
            result["content_risk"]["boundary"],
            "本层只基于标题和正文做编辑复核；图片、封面、评论区、账号资料和视频字幕需另行检查。",
        )

    def test_html_does_not_emit_invented_read_scenarios(self):
        result = detector.detect(
            "AI漫剧创作者现状：高成本、低胜率，但机会正在洗牌",
            "2026年AI漫剧市场拥挤，创作者需要先看清成本、产量和投测路径，再决定怎么走。",
            track="tech",
        )
        html = detector.fmt_html(result)
        self.assertIn("缺少真实账号数据", html)
        self.assertIn("不是爆款概率", html)
        self.assertNotIn("假设粉丝规模阅读情景", html)
        self.assertNotIn("宇宙第一爆款检测", html)


if __name__ == "__main__":
    unittest.main()
