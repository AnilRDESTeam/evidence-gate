"""Tests for the Challenger prompt template and the two hand-test scripts."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPT = ROOT / "src" / "evidence_gate" / "challenger" / "prompt.md"
SAMPLE = ROOT / "docs" / "challenger" / "sample"
SCHEMA = ROOT / "contract" / "challenge.schema.json"
EXAMPLE = ROOT / "contract" / "examples" / "challenge.example.json"
TOKENS = ["{task_yaml}", "{commit}", "{diff}", "{files}"]


def run(script, *args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                          capture_output=True, text=True)


def fill(tmp_path):
    out = tmp_path / "prompt.md"
    result = run("fill_challenge_prompt.py", "--task", SAMPLE / "task.yaml", "--diff", SAMPLE / "change.diff",
                 "--files", SAMPLE / "changed_files.txt", "--commit", "a41c9e2", "--out", out)
    assert result.returncode == 0, result.stderr
    return out.read_text(encoding="utf-8"), result.stdout


def test_template_has_each_token_once():
    text = PROMPT.read_text(encoding="utf-8")
    for token in TOKENS:
        assert text.count(token) == 1, token


def test_fill_leaves_no_tokens(tmp_path):
    text, _ = fill(tmp_path)
    for token in TOKENS:
        assert token not in text
    assert "SHOP-102" in text and "a41c9e2" in text


def test_printed_hash_is_template_sha256(tmp_path):
    _, stdout = fill(tmp_path)
    template = PROMPT.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert hashlib.sha256(template.encode("utf-8")).hexdigest() in stdout


def test_validate_json_accepts_example():
    assert run("validate_json.py", SCHEMA, EXAMPLE).stdout.strip() == "OK"


def test_validate_json_rejects_six_scenarios(tmp_path):
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["proposed_scenarios"] = [data["proposed_scenarios"][0]] * 6
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    result = run("validate_json.py", SCHEMA, bad)
    assert result.returncode == 1
    assert "proposed_scenarios" in result.stdout


def test_validate_json_accepts_fenced_answer(tmp_path):
    fenced = tmp_path / "fenced.json"
    fenced.write_text("```json\n" + EXAMPLE.read_text(encoding="utf-8") + "\n```\n", encoding="utf-8")
    assert run("validate_json.py", SCHEMA, fenced).stdout.strip() == "OK"
