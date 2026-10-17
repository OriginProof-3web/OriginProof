import json
import warnings
from pathlib import Path

import pytest
from originproof_analyzer.errors import AnalyzerError
from originproof_analyzer.evaluation import evaluate
from originproof_analyzer.inputs import SemanticInput
from originproof_analyzer.providers import MockLLMProvider
from originproof_analyzer.service import SemanticInterface
from originproof_core import CardPaymentNoticeCandidate

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures/mvp/analyzer_cases.json"


def test_evaluation_reports_mock_scope_and_real_denominators():
    report = evaluate(FIXTURE)
    assert report["passed"] == report["total"] == 10
    assert report["live_model_evaluated"] is False
    assert report["confidence_is_calibrated"] is False
    assert report["candidate_outputs_are_unconfirmed"] is True
    assert report["artifact_comparison_performed"] is False
    assert report["image_mode"] == "fixture_replay_only"
    assert report["fields"]["amount_minor"] == {
        "matched": 8,
        "total": 8,
        "present_matched": 8,
        "present_total": 8,
    }
    assert report["fields"]["transaction_id"]["present_total"] == 7


def test_evaluation_detects_wrong_expected_amount(tmp_path):
    manifest = json.loads(FIXTURE.read_text())
    manifest["cases"][0]["expected"]["amount_minor"] = 1
    fixture = tmp_path / "synthetic.json"
    fixture.write_text(json.dumps(manifest))
    report = evaluate(fixture)
    assert report["passed"] == 8 and report["total"] == 10


@pytest.mark.parametrize("changes", [{"amount_minor": "154000"}, {"confidence": 1.2}])
def test_domain_revalidates_bypassed_model_instances(normal_case, changes):
    values = CardPaymentNoticeCandidate.model_validate(normal_case["expected"]).model_dump()

    class BrokenProvider(MockLLMProvider):
        def extract_card_payment_notice(self, artifact):
            return CardPaymentNoticeCandidate.model_construct(**{**values, **changes})

    with pytest.raises(AnalyzerError) as caught:
        SemanticInterface(BrokenProvider()).analyze_card_payment_notice(
            SemanticInput(text="synthetic")
        )
    assert caught.value.code == "SCHEMA_MISMATCH"


def test_invalid_provider_objects_do_not_leak_in_warnings(normal_case):
    values = CardPaymentNoticeCandidate.model_validate(normal_case["expected"]).model_dump()

    class BrokenProvider(MockLLMProvider):
        def extract_card_payment_notice(self, artifact):
            return CardPaymentNoticeCandidate.model_construct(
                **{**values, "amount_minor": "PRIVATE_PROVIDER_VALUE"}
            )

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with pytest.raises(AnalyzerError):
            SemanticInterface(BrokenProvider()).analyze_card_payment_notice(
                SemanticInput(text="PRIVATE_INPUT")
            )
    assert captured == []


def test_input_repr_and_validation_message_are_redacted():
    assert "PRIVATE" not in repr(SemanticInput(text="PRIVATE_INPUT"))
    with pytest.raises(ValueError) as caught:
        SemanticInput(image_base64="PRIVATE_IMAGE", image_media_type="image/png")
    assert "PRIVATE" not in str(caught.value)
