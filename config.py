from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIALOG_DIR = WORKSPACE_ROOT / "testChatBot" / "vedio"
DEFAULT_LEGACY_EVAL_DIR = WORKSPACE_ROOT / "voice_test"


def _first_excel_file(directory: Path) -> Optional[Path]:
    if not directory.exists():
        return None

    preferred = directory / "E2E情感陪聊数据集_pre_3.xlsx"
    if preferred.exists():
        return preferred

    candidates = sorted(directory.glob("*.xlsx"))
    return candidates[0] if candidates else None


def _default_test_case_file() -> Path:
    return _first_excel_file(DEFAULT_LEGACY_EVAL_DIR) or (
        DEFAULT_LEGACY_EVAL_DIR / "E2E情感陪聊数据集_pre_3.xlsx"
    )


@dataclass(frozen=True)
class EvaluationConfig:
    workspace_root: Path = WORKSPACE_ROOT
    dialog_dir: Path = DEFAULT_DIALOG_DIR
    legacy_eval_dir: Path = DEFAULT_LEGACY_EVAL_DIR
    ws_host: str = "localhost"
    ws_port: int = 8765
    client_id_prefix: str = "eval_client"
    test_case_file: Path = _default_test_case_file()
    test_case_sheet: str = "Sheet2"
    start_row: int = 2
    pre_wav_path: Path = DEFAULT_LEGACY_EVAL_DIR / "output_recording.wav"
    audio_input_dir: Path = DEFAULT_LEGACY_EVAL_DIR / "voice_input_file"
    output_dir: Path = WORKSPACE_ROOT / "integrated_voice_eval" / "output"
    audio_output_dir: Path = WORKSPACE_ROOT / "integrated_voice_eval" / "output" / "voice_output"
    result_file: Path = WORKSPACE_ROOT / "integrated_voice_eval" / "output" / "eval_results.xlsx"
    chunk_size: int = 4096
    timeout_seconds: int = 30
    silence_duration_ms: int = 1000
    sample_rate: int = 16000
    leading_silence_files: int = 3
    trailing_silence_files: int = 3
    case_id_column: str = "用例子编号"
    audio_file_column: str = "音频文件路径"
    response_column: str = "回复的内容"
    emotion_column: str = "识别到的情绪"
    llm_emotion_column: str = "回复的情绪"
    saved_audio_column: str = "回复语音保存路径"

    @property
    def ws_uri_template(self) -> str:
        return f"ws://{self.ws_host}:{self.ws_port}/ws/{{client_id}}"

    def with_overrides(self, **kwargs: object) -> "EvaluationConfig":
        return replace(self, **kwargs)

    def ensure_output_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audio_output_dir.mkdir(parents=True, exist_ok=True)
