from __future__ import annotations

import io
import json
import urllib.error

import pytest

from app import agents
from app.agents import (
    FALLBACK_FLAG_TEMPLATE,
    _append_fallback_flag,
    _chat_completion_json,
    _compliance_prompt,
    _env_enabled,
    _llm_runtime_config,
    _run_compliance_agent_with_fallback,
    _run_scoring_agent_with_fallback,
    _scoring_prompt,
    _strip_json_fences,
    compliance_and_fraud_agent,
    get_orchestration_status,
    income_stability_agent,
    run_all_agents,
)
from app.schemas import AgentScoreOutput, ComplianceAgentOutput
from tests.factories import strong_borrower, weak_borrower

pytestmark = pytest.mark.asyncio


def llm_config(**overrides):
    config = {
        "mode": "llm_parallel",
        "llm_requested": True,
        "llm_enabled": True,
        "api_key_present": True,
        "model": "gpt-4.1-mini",
        "endpoint": "https://llm.test/v1/chat/completions",
        "timeout_seconds": 14,
    }
    config.update(overrides)
    return config


def scored(score: int = 77, flags=None) -> AgentScoreOutput:
    return AgentScoreOutput(
        score=score,
        confidence="high",
        reasoning="Synthetic LLM output used by the test suite.",
        flags=flags or [],
    )


def chat_response(content: str) -> bytes:
    return json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False


def patch_urlopen(monkeypatch, body: bytes = None, error: Exception = None, capture=None):
    def fake(request, timeout=None):
        if capture is not None:
            capture["url"] = request.full_url
            capture["headers"] = dict(request.headers)
            capture["body"] = json.loads(request.data)
            capture["timeout"] = timeout
        if error is not None:
            raise error
        return FakeResponse(body)

    monkeypatch.setattr(agents.urllib.request, "urlopen", fake)


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on"])
async def test_truthy_switches_enable(monkeypatch, value):
    monkeypatch.setenv("CREDIBLE_LLM_ORCHESTRATION", value)
    assert _env_enabled("CREDIBLE_LLM_ORCHESTRATION") is True


@pytest.mark.parametrize("value", ["false", "0", "no", "", "maybe"])
async def test_anything_else_leaves_it_off(monkeypatch, value):
    monkeypatch.setenv("CREDIBLE_LLM_ORCHESTRATION", value)
    assert _env_enabled("CREDIBLE_LLM_ORCHESTRATION") is False


async def test_the_llm_is_off_by_default(monkeypatch):
    monkeypatch.delenv("CREDIBLE_LLM_ORCHESTRATION", raising=False)
    monkeypatch.delenv("CREDIBLE_LLM_API_KEY", raising=False)

    config = _llm_runtime_config()

    assert config["llm_enabled"] is False
    assert config["mode"] == "rules_parallel"


async def test_requesting_the_llm_without_a_key_does_not_enable_it(monkeypatch):
    monkeypatch.setenv("CREDIBLE_LLM_ORCHESTRATION", "true")
    monkeypatch.delenv("CREDIBLE_LLM_API_KEY", raising=False)

    config = _llm_runtime_config()

    assert config["llm_requested"] is True
    assert config["api_key_present"] is False
    assert config["llm_enabled"] is False
    assert config["mode"] == "rules_parallel"


async def test_a_key_and_a_request_together_enable_it(monkeypatch):
    monkeypatch.setenv("CREDIBLE_LLM_ORCHESTRATION", "true")
    monkeypatch.setenv("CREDIBLE_LLM_API_KEY", "sk-test")

    config = _llm_runtime_config()

    assert config["llm_enabled"] is True
    assert config["mode"] == "llm_parallel"


async def test_a_blank_key_does_not_count(monkeypatch):
    monkeypatch.setenv("CREDIBLE_LLM_ORCHESTRATION", "true")
    monkeypatch.setenv("CREDIBLE_LLM_API_KEY", "   ")

    assert _llm_runtime_config()["llm_enabled"] is False


@pytest.mark.parametrize("raw,expected", [("3", 5), ("14", 14), ("500", 90), ("nonsense", 14)])
async def test_the_timeout_is_clamped_and_defaulted(monkeypatch, raw, expected):
    monkeypatch.setenv("CREDIBLE_LLM_TIMEOUT_SECONDS", raw)

    assert _llm_runtime_config()["timeout_seconds"] == expected


async def test_the_status_endpoint_never_leaks_the_key(monkeypatch):
    monkeypatch.setenv("CREDIBLE_LLM_ORCHESTRATION", "true")
    monkeypatch.setenv("CREDIBLE_LLM_API_KEY", "sk-super-secret-value")

    status = get_orchestration_status()

    assert "sk-super-secret-value" not in json.dumps(status)
    assert status["api_key_present"] is True


async def test_the_status_lists_every_agent():
    assert set(get_orchestration_status()["parallel_agents"]) == {
        "income",
        "repayment",
        "lifestyle",
        "compliance",
    }


@pytest.mark.parametrize(
    "raw",
    [
        '{"score": 70}',
        '```json\n{"score": 70}\n```',
        '```\n{"score": 70}\n```',
        '  {"score": 70}  ',
    ],
)
async def test_json_survives_however_it_is_fenced(raw):
    assert json.loads(_strip_json_fences(raw)) == {"score": 70}


async def test_a_well_formed_response_is_parsed(monkeypatch):
    patch_urlopen(monkeypatch, body=chat_response('{"score": 81}'))

    result = _chat_completion_json(
        endpoint="https://llm.test/v1/chat/completions",
        api_key="sk-test",
        model="gpt-4.1-mini",
        timeout_seconds=14,
        system_prompt="system",
        user_prompt="user",
    )

    assert result == {"score": 81}


async def test_the_request_carries_the_key_model_and_json_mode(monkeypatch):
    captured: dict = {}
    patch_urlopen(monkeypatch, body=chat_response("{}"), capture=captured)

    _chat_completion_json(
        endpoint="https://llm.test/v1/chat/completions",
        api_key="sk-test",
        model="gpt-4.1-mini",
        timeout_seconds=14,
        system_prompt="system",
        user_prompt="user",
    )

    assert captured["url"] == "https://llm.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["body"]["model"] == "gpt-4.1-mini"
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert captured["timeout"] == 14


async def test_a_low_temperature_is_requested(monkeypatch):
    captured: dict = {}
    patch_urlopen(monkeypatch, body=chat_response("{}"), capture=captured)

    _chat_completion_json(
        endpoint="https://llm.test/v1/chat/completions",
        api_key="sk-test",
        model="m",
        timeout_seconds=5,
        system_prompt="system",
        user_prompt="user",
    )

    assert captured["body"]["temperature"] <= 0.2


async def test_segmented_content_is_reassembled(monkeypatch):
    body = json.dumps(
        {
            "choices": [
                {"message": {"content": [{"text": '{"score":'}, {"text": " 64}"}]}}
            ]
        }
    ).encode("utf-8")
    patch_urlopen(monkeypatch, body=body)

    result = _chat_completion_json(
        endpoint="https://llm.test/v1/chat/completions",
        api_key="k", model="m", timeout_seconds=5,
        system_prompt="s", user_prompt="u",
    )

    assert result == {"score": 64}


@pytest.mark.parametrize(
    "body",
    [
        b'{"choices": []}',
        b'{}',
        b'{"choices": ["not-a-dict"]}',
        b'{"choices": [{"message": "not-a-dict"}]}',
        b'{"choices": [{"message": {"content": ""}}]}',
        b'{"choices": [{"message": {"content": null}}]}',
    ],
)
async def test_a_malformed_response_raises(monkeypatch, body):
    patch_urlopen(monkeypatch, body=body)

    with pytest.raises((ValueError, json.JSONDecodeError)):
        _chat_completion_json(
            endpoint="https://llm.test/v1/chat/completions",
            api_key="k", model="m", timeout_seconds=5,
            system_prompt="s", user_prompt="u",
        )


async def test_non_json_content_raises(monkeypatch):
    patch_urlopen(monkeypatch, body=chat_response("I am not JSON at all."))

    with pytest.raises(json.JSONDecodeError):
        _chat_completion_json(
            endpoint="https://llm.test/v1/chat/completions",
            api_key="k", model="m", timeout_seconds=5,
            system_prompt="s", user_prompt="u",
        )


async def test_a_network_failure_propagates(monkeypatch):
    patch_urlopen(monkeypatch, error=urllib.error.URLError("connection refused"))

    with pytest.raises(urllib.error.URLError):
        _chat_completion_json(
            endpoint="https://llm.test/v1/chat/completions",
            api_key="k", model="m", timeout_seconds=5,
            system_prompt="s", user_prompt="u",
        )


async def test_the_scoring_prompt_carries_the_payload_and_asks_for_json():
    prompt = _scoring_prompt("Income Stability", strong_borrower())

    assert "Income Stability" in prompt
    assert "JSON" in prompt
    assert "Strong Borrower" in prompt


async def test_the_compliance_prompt_asks_for_its_own_fields():
    prompt = _compliance_prompt(strong_borrower())

    assert "rbi_compliant" in prompt
    assert "fraud_risk" in prompt


async def test_the_prompt_is_ascii_safe():
    prompt = _scoring_prompt("Income Stability", strong_borrower(borrower_name="Ravi Kumar"))

    prompt.encode("ascii")


async def test_the_rules_agent_runs_when_the_llm_is_off():
    called = {"llm": False}

    async def llm_runner(payload, **kwargs):
        called["llm"] = True
        return scored()

    result = await _run_scoring_agent_with_fallback(
        strong_borrower(),
        agent_name="income",
        llm_enabled=False,
        llm_config=llm_config(llm_enabled=False),
        llm_runner=llm_runner,
        rules_runner=income_stability_agent,
    )

    assert called["llm"] is False
    assert result.score == (await income_stability_agent(strong_borrower())).score


async def test_the_llm_result_is_used_when_it_succeeds(monkeypatch):
    monkeypatch.setenv("CREDIBLE_LLM_API_KEY", "sk-test")

    async def llm_runner(payload, **kwargs):
        return scored(score=91)

    result = await _run_scoring_agent_with_fallback(
        strong_borrower(),
        agent_name="income",
        llm_enabled=True,
        llm_config=llm_config(),
        llm_runner=llm_runner,
        rules_runner=income_stability_agent,
    )

    assert result.score == 91


async def test_the_llm_runner_is_given_the_configured_endpoint(monkeypatch):
    monkeypatch.setenv("CREDIBLE_LLM_API_KEY", "sk-test")
    seen: dict = {}

    async def llm_runner(payload, **kwargs):
        seen.update(kwargs)
        return scored()

    await _run_scoring_agent_with_fallback(
        strong_borrower(),
        agent_name="income",
        llm_enabled=True,
        llm_config=llm_config(endpoint="https://custom.test/v1", model="custom-model"),
        llm_runner=llm_runner,
        rules_runner=income_stability_agent,
    )

    assert seen["endpoint"] == "https://custom.test/v1"
    assert seen["model"] == "custom-model"
    assert seen["api_key"] == "sk-test"


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.URLError("down"),
        TimeoutError("slow"),
        ValueError("bad shape"),
        json.JSONDecodeError("bad", "doc", 0),
        KeyError("missing"),
        TypeError("wrong type"),
    ],
)
async def test_every_llm_failure_falls_back_to_rules(failure):
    async def llm_runner(payload, **kwargs):
        raise failure

    result = await _run_scoring_agent_with_fallback(
        strong_borrower(),
        agent_name="income",
        llm_enabled=True,
        llm_config=llm_config(),
        llm_runner=llm_runner,
        rules_runner=income_stability_agent,
    )

    assert isinstance(result, AgentScoreOutput)
    assert 0 <= result.score <= 100


async def test_a_fallback_is_disclosed_in_the_flags():
    async def llm_runner(payload, **kwargs):
        raise urllib.error.URLError("down")

    result = await _run_scoring_agent_with_fallback(
        strong_borrower(),
        agent_name="income",
        llm_enabled=True,
        llm_config=llm_config(),
        llm_runner=llm_runner,
        rules_runner=income_stability_agent,
    )

    note = FALLBACK_FLAG_TEMPLATE.format(agent="income")
    assert note in result.flags


async def test_a_successful_llm_call_carries_no_fallback_flag():
    async def llm_runner(payload, **kwargs):
        return scored()

    result = await _run_scoring_agent_with_fallback(
        strong_borrower(),
        agent_name="income",
        llm_enabled=True,
        llm_config=llm_config(),
        llm_runner=llm_runner,
        rules_runner=income_stability_agent,
    )

    assert not any("deterministic rules" in flag for flag in result.flags)


async def test_the_flag_keeps_the_agents_own_flags():
    async def llm_runner(payload, **kwargs):
        raise ValueError("bad")

    result = await _run_scoring_agent_with_fallback(
        weak_borrower(),
        agent_name="income",
        llm_enabled=True,
        llm_config=llm_config(),
        llm_runner=llm_runner,
        rules_runner=income_stability_agent,
    )
    rules_only = await income_stability_agent(weak_borrower())

    for flag in rules_only.flags:
        assert flag in result.flags


async def test_the_flag_is_not_added_twice():
    once = _append_fallback_flag(scored(), "income")
    twice = _append_fallback_flag(once, "income")

    assert once.flags == twice.flags


async def test_a_compliance_fallback_is_also_disclosed(monkeypatch):
    patch_urlopen(monkeypatch, error=urllib.error.URLError("down"))

    result = await _run_compliance_agent_with_fallback(
        strong_borrower(),
        llm_enabled=True,
        llm_config=llm_config(),
    )

    assert isinstance(result, ComplianceAgentOutput)
    assert any("deterministic rules" in flag for flag in result.flags)


async def test_compliance_uses_the_llm_when_it_answers(monkeypatch):
    patch_urlopen(
        monkeypatch,
        body=chat_response(
            json.dumps(
                {
                    "rbi_compliant": False,
                    "fraud_risk": "high",
                    "flags": ["Synthetic flag"],
                    "notes": "Synthetic compliance output for the suite.",
                }
            )
        ),
    )

    result = await _run_compliance_agent_with_fallback(
        strong_borrower(), llm_enabled=True, llm_config=llm_config()
    )

    assert result.rbi_compliant is False
    assert result.fraud_risk == "high"


async def test_compliance_uses_rules_when_the_llm_is_off():
    result = await _run_compliance_agent_with_fallback(
        strong_borrower(), llm_enabled=False, llm_config=llm_config(llm_enabled=False)
    )
    rules = await compliance_and_fraud_agent(strong_borrower())

    assert result.fraud_risk == rules.fraud_risk
    assert result.flags == rules.flags


async def test_an_unexpected_error_is_not_swallowed():
    async def llm_runner(payload, **kwargs):
        raise MemoryError("out of memory")

    with pytest.raises(MemoryError):
        await _run_scoring_agent_with_fallback(
            strong_borrower(),
            agent_name="income",
            llm_enabled=True,
            llm_config=llm_config(),
            llm_runner=llm_runner,
            rules_runner=income_stability_agent,
        )


async def test_the_orchestrator_uses_the_llm_when_it_is_configured(monkeypatch):
    monkeypatch.setenv("CREDIBLE_LLM_ORCHESTRATION", "true")
    monkeypatch.setenv("CREDIBLE_LLM_API_KEY", "sk-test")
    patch_urlopen(
        monkeypatch,
        body=chat_response(
            json.dumps(
                {
                    "score": 88,
                    "confidence": "high",
                    "reasoning": "Synthetic LLM scoring output for the suite.",
                    "flags": [],
                }
            )
        ),
    )

    outputs = await run_all_agents(strong_borrower())

    assert outputs["income"].score == 88
    assert outputs["repayment"].score == 88


async def test_the_orchestrator_falls_back_when_the_llm_is_down(monkeypatch):
    monkeypatch.setenv("CREDIBLE_LLM_ORCHESTRATION", "true")
    monkeypatch.setenv("CREDIBLE_LLM_API_KEY", "sk-test")
    patch_urlopen(monkeypatch, error=urllib.error.URLError("connection refused"))

    outputs = await run_all_agents(strong_borrower())
    rules = await income_stability_agent(strong_borrower())

    assert outputs["income"].score == rules.score
    assert any("deterministic rules" in flag for flag in outputs["income"].flags)


async def test_one_failing_agent_does_not_take_the_others_down(monkeypatch):
    monkeypatch.setenv("CREDIBLE_LLM_ORCHESTRATION", "true")
    monkeypatch.setenv("CREDIBLE_LLM_API_KEY", "sk-test")

    calls = {"n": 0}
    good = chat_response(
        json.dumps(
            {
                "score": 73,
                "confidence": "medium",
                "reasoning": "Synthetic LLM scoring output for the suite.",
                "flags": [],
            }
        )
    )

    def fake(request, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.URLError("first one fails")
        return FakeResponse(good)

    monkeypatch.setattr(agents.urllib.request, "urlopen", fake)

    outputs = await run_all_agents(strong_borrower())

    scores = [outputs[name].score for name in ("income", "repayment", "lifestyle")]
    assert 73 in scores
    assert all(0 <= score <= 100 for score in scores)
