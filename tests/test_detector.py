import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import detector  # noqa: E402


class DetectorRegressionTests(unittest.TestCase):
    def test_single_character_superlative_is_not_a_false_positive(self):
        issues = detector.compliance_check(
            "这是我见过最普通的一天",
            "今天下班回家，买了菜，吃完饭后看了一会儿书。",
            "general",
        )
        self.assertFalse(any(i["line"] == "平台极限词(小红书/抖音严打)" for i in issues))

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
        self.assertFalse(any("医疗功效词" in i["line"] for i in issues))

    def test_positive_medical_claim_remains_a_review_hit(self):
        issues = detector.compliance_check(
            "健康方法",
            "这种方法可以治疗失眠。",
            "health",
        )
        self.assertTrue(any("医疗功效词" in i["line"] for i in issues))

    def test_missing_fans_does_not_invent_read_count(self):
        result = detector.detect("普通的一天", "今天下班后回家，安静地吃了晚饭。", fans=None)
        self.assertIsNone(result["predict"]["predict"])
        self.assertEqual(result["predict"]["confidence"], "low")
        self.assertEqual(
            [item["fans"] for item in result["predict"]["scenario_reads"]],
            [1000, 10000, 100000],
        )

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


if __name__ == "__main__":
    unittest.main()
