from __future__ import annotations

import asyncio
import base64
import json
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional

import websockets
from pydub import AudioSegment

from config import EvaluationConfig


def merge_wav_chunks(chunks: List[bytes]) -> bytes:
    if not chunks:
        return b""
    if len(chunks) == 1:
        return chunks[0]

    pcm_parts: List[bytes] = []
    first_header: Optional[bytes] = None
    for chunk in chunks:
        if len(chunk) >= 44 and chunk[:4] == b"RIFF":
            if first_header is None:
                first_header = chunk[:44]
            pcm_parts.append(chunk[44:])
        else:
            pcm_parts.append(chunk)

    if first_header is None:
        return b"".join(chunks)

    pcm_data = b"".join(pcm_parts)
    merged = bytearray(first_header)
    struct.pack_into("<I", merged, 4, len(pcm_data) + 36)
    struct.pack_into("<I", merged, 40, len(pcm_data))
    return bytes(merged) + pcm_data


class VoiceTestClient:
    def __init__(self, config: EvaluationConfig):
        self.config = config

    def _build_case_audio(self, case_dict: Dict[str, Any]) -> bytes:
        audio_name = str(case_dict.get(self.config.audio_file_column, "")).strip()
        if not audio_name:
            raise ValueError(
                f"测试用例缺少列 `{self.config.audio_file_column}` 对应的音频文件名"
            )

        audio_path = self.config.audio_input_dir / audio_name
        if not audio_path.exists():
            raise FileNotFoundError(f"测试音频不存在: {audio_path}")

        audio_files = (
            [self.config.pre_wav_path] * self.config.leading_silence_files
            + [audio_path]
            + [self.config.pre_wav_path] * self.config.trailing_silence_files
        )

        missing = [str(path) for path in audio_files if not path.exists()]
        if missing:
            raise FileNotFoundError(f"缺少前置或尾部静音文件: {missing}")

        combined_audio = AudioSegment.empty()
        for file_path in audio_files:
            audio = AudioSegment.from_wav(file_path)
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            combined_audio += audio
        return combined_audio.raw_data

    async def _send_silence(self, websocket: websockets.ClientConnection) -> None:
        num_samples = int(
            self.config.sample_rate * self.config.silence_duration_ms / 1000
        )
        silence_pcm = bytes(num_samples * 2)
        for index in range(0, len(silence_pcm), self.config.chunk_size):
            await websocket.send(silence_pcm[index : index + self.config.chunk_size])
            await asyncio.sleep(0.1)

    async def _send_audio(
        self,
        websocket: websockets.ClientConnection,
        case_dict: Dict[str, Any],
    ) -> None:
        pcm_data = self._build_case_audio(case_dict)
        for index in range(0, len(pcm_data), self.config.chunk_size):
            await websocket.send(pcm_data[index : index + self.config.chunk_size])
        await asyncio.sleep(2)
        await self._send_silence(websocket)

    def _save_audio(self, case_id: str, audio_chunks: List[bytes]) -> Path:
        output_path = self.config.audio_output_dir / f"{case_id}_output.wav"
        output_path.write_bytes(merge_wav_chunks(audio_chunks))
        return output_path

    async def _receive_response(
        self,
        websocket: websockets.ClientConnection,
        case_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        audio_chunks: List[bytes] = []
        llm_chunks: List[str] = []

        while True:
            response = await asyncio.wait_for(
                websocket.recv(),
                timeout=self.config.timeout_seconds,
            )
            if isinstance(response, bytes):
                continue

            data = json.loads(response)
            message_type = data.get("type")
            if message_type == "latency_update":
                continue
            if message_type == "llm_chunk":
                llm_chunks.append(data.get("data", {}).get("text", ""))
                continue
            if message_type == "audio_chunk":
                audio_base64 = data.get("data", {}).get("audio", "")
                if audio_base64:
                    audio_chunks.append(base64.b64decode(audio_base64))
                continue
            if message_type != "result":
                continue

            result_data = data.get("data", {})
            case_id = str(case_dict.get(self.config.case_id_column, "unknown"))
            saved_audio_path = ""
            if audio_chunks:
                saved_audio_path = str(self._save_audio(case_id, audio_chunks))

            case_dict[self.config.response_column] = result_data.get(
                "response", "".join(llm_chunks)
            )
            case_dict[self.config.emotion_column] = result_data.get("emotion", "")
            case_dict[self.config.llm_emotion_column] = result_data.get(
                "llm_emotion", ""
            )
            case_dict[self.config.saved_audio_column] = saved_audio_path
            case_dict["dialog_text"] = result_data.get("text", "")
            case_dict["query_id"] = data.get("query_id", "")
            return case_dict

    async def run_test(self, case_dict: Dict[str, Any], case_index: int) -> Dict[str, Any]:
        client_id = f"{self.config.client_id_prefix}_{case_index}"
        ws_uri = self.config.ws_uri_template.format(client_id=client_id)

        async with websockets.connect(ws_uri, max_size=None) as websocket:
            send_task = asyncio.create_task(self._send_audio(websocket, case_dict))
            receive_task = asyncio.create_task(
                self._receive_response(websocket, case_dict)
            )
            await send_task
            return await receive_task
