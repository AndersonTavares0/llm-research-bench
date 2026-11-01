import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "tools" / "homelab" / "campaign-entrypoint.sh"
GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.is_file() else shutil.which("bash")


@pytest.mark.skipif(BASH is None, reason="Bash is required to exercise the GPU Lab entrypoint")
def test_unknown_task_is_rejected_before_workspace_side_effects(tmp_path):
    workspace = tmp_path / "workspace"
    env = os.environ.copy()
    env.update(WORKSPACE=str(workspace), GPU_LAB_TASK="campaign; arbitrary-command")

    result = subprocess.run(
        [BASH, str(ENTRYPOINT)], env=env, capture_output=True, text=True, timeout=20
    )

    assert "unsupported GPU_LAB_TASK" in result.stderr
    assert result.returncode == 2
    assert not (workspace / ".tmp").exists()


def test_entrypoint_whitelists_only_campaign_and_paired_diagnostic():
    source = ENTRYPOINT.read_text(encoding="utf-8")
    assert re.search(
        r'GPU_LAB_TASK="\$\{GPU_LAB_TASK:-campaign\}"', source
    )
    selector = re.search(r"case \"\$GPU_LAB_TASK\" in(?P<body>.*?)esac", source, re.S)
    assert selector
    assert re.search(r"campaign\)", selector["body"])
    assert re.search(r"gsm8k-paired\)", selector["body"])
    assert re.search(r"\*\).*unsupported GPU_LAB_TASK", selector["body"], re.S)


def test_paired_task_uses_only_fixed_diagnostic_and_pinned_inputs():
    source = ENTRYPOINT.read_text(encoding="utf-8")
    assert '"$REPO/tools/homelab/gsm8k-diagnostic.sh"' in source
    assert "qwen3-1.7b" in source
    assert "d6de81643928d653435c431bae19945d41d32520" in source
    assert "GPU_LAB_COMMAND" not in source


def test_campaign_remains_the_default_full_campaign_route():
    source = ENTRYPOINT.read_text(encoding="utf-8")
    assert 'GPU_LAB_TASK="${GPU_LAB_TASK:-campaign}"' in source
    assert '"$VENV/bin/python" -m llm_research_bench.campaign run' in source
    assert '"$VENV/bin/python" -m llm_research_bench.campaign summary' in source


@pytest.mark.skipif(BASH is None, reason="Bash is required to exercise the paired wrapper")
def test_fixed_paired_wrapper_overrides_task_and_execs_adjacent_entrypoint(tmp_path):
    wrapper = ROOT / "tools/homelab/gsm8k-paired-entrypoint.sh"
    if not wrapper.is_file():
        pytest.fail("fixed paired-task wrapper does not exist")

    wrapper_copy = tmp_path / "gsm8k-paired-entrypoint.sh"
    wrapper_copy.write_bytes(wrapper.read_bytes())
    (tmp_path / "campaign-entrypoint.sh").write_text(
        'printf "%s" "$GPU_LAB_TASK" > "$TASK_CAPTURE"\n', encoding="utf-8"
    )
    capture = tmp_path / "task.txt"
    result = subprocess.run(
        [BASH, str(wrapper_copy)],
        env={**os.environ, "GPU_LAB_TASK": "campaign", "TASK_CAPTURE": str(capture)},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert capture.read_text(encoding="utf-8") == "gsm8k-paired"
