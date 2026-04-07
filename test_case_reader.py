from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def read_test_cases(
    file_path: Path,
    sheet_name: str,
    start_row: int = 2,
) -> List[Dict[str, Any]]:
    dataframe = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")

    test_cases: List[Dict[str, Any]] = []
    for index, row in dataframe.iterrows():
        if index + 1 < start_row:
            continue
        if row.isna().all():
            continue
        case = {
            key: ("" if pd.isna(value) else value)
            for key, value in row.to_dict().items()
        }
        test_cases.append(case)
    return test_cases


def save_test_results(results: List[Dict[str, Any]], output_file: Path) -> None:
    dataframe = pd.DataFrame(results)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_excel(output_file, index=False, engine="openpyxl")
