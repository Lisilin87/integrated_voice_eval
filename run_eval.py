from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any, Dict, List

from config import EvaluationConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run voice evaluation against testChatBot/vedio websocket service."
    )
    parser.add_argument("--ws-host", default="localhost")
    parser.add_argument("--ws-port", type=int, default=8765)
    parser.add_argument("--sheet", default="Sheet2")
    parser.add_argument("--start-row", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--client-id-prefix", default="eval_client")
    parser.add_argument("--test-case-file", type=Path)
    parser.add_argument("--audio-input-dir", type=Path)
    parser.add_argument("--pre-wav-path", type=Path)
    parser.add_argument("--result-file", type=Path)
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> EvaluationConfig:
    config = EvaluationConfig().with_overrides(
        ws_host=args.ws_host,
        ws_port=args.ws_port,
        test_case_sheet=args.sheet,
        start_row=args.start_row,
        client_id_prefix=args.client_id_prefix,
    )
    if args.test_case_file:
        config = config.with_overrides(test_case_file=args.test_case_file.resolve())
    if args.audio_input_dir:
        config = config.with_overrides(audio_input_dir=args.audio_input_dir.resolve())
    if args.pre_wav_path:
        config = config.with_overrides(pre_wav_path=args.pre_wav_path.resolve())
    if args.result_file:
        result_file = args.result_file.resolve()
        config = config.with_overrides(
            result_file=result_file,
            output_dir=result_file.parent,
            audio_output_dir=result_file.parent / "voice_output",
        )
    return config


async def run_all_tests(config: EvaluationConfig, limit: int = 0) -> List[Dict[str, Any]]:
    from test_case_reader import read_test_cases, save_test_results
    from voice_test_client import VoiceTestClient

    if not config.test_case_file.exists():
        raise FileNotFoundError(
            f"测试用例文件不存在: {config.test_case_file}\n"
            "请通过 --test-case-file 指定，或将 Excel 放到 voice_test 目录。"
        )

    config.ensure_output_dirs()
    test_cases = read_test_cases(
        config.test_case_file,
        config.test_case_sheet,
        config.start_row,
    )
    if limit > 0:
        test_cases = test_cases[:limit]
    if not test_cases:
        raise RuntimeError("没有读取到任何测试用例。")

    client = VoiceTestClient(config)
    results: List[Dict[str, Any]] = []

    print("=" * 60)
    print("Voice Evaluation Bridge")
    print("=" * 60)
    print(f"vedio service : {config.ws_host}:{config.ws_port}")
    print(f"test cases    : {config.test_case_file}")
    print(f"output file   : {config.result_file}")
    print(f"case count    : {len(test_cases)}")

    for index, case_dict in enumerate(test_cases, start=1):
        case_id = case_dict.get(config.case_id_column, index)
        print(f"\n[{index}/{len(test_cases)}] case={case_id}")
        try:
            result = await client.run_test(case_dict, index)
            result["status"] = "ok"
            results.append(result)
            print("status        : ok")
        except Exception as exc:
            failed_case = dict(case_dict)
            failed_case["status"] = "error"
            failed_case["error"] = str(exc)
            results.append(failed_case)
            print(f"status        : error ({exc})")

        save_test_results(results, config.result_file)

    return results


def main() -> None:
    args = parse_args()
    config = build_config(args)
    try:
        results = asyncio.run(run_all_tests(config, limit=args.limit))
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f"缺少依赖: {exc.name}。请先在 "
            f"{config.workspace_root / 'integrated_voice_eval'} "
            "执行 `pip install -r requirements.txt`。"
        ) from exc
    success_count = sum(1 for item in results if item.get("status") == "ok")
    failure_count = len(results) - success_count

    print("\n" + "=" * 60)
    print("Completed")
    print("=" * 60)
    print(f"success       : {success_count}")
    print(f"failure       : {failure_count}")
    print(f"result file   : {config.result_file}")


if __name__ == "__main__":
    main()
