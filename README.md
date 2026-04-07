# Integrated Voice Eval

这个目录用于把两套能力真正串起来：

- `testChatBot/vedio` 提供全双工语音对话 WebSocket 服务
- `voice_test` 提供历史评估数据格式、音频资源和 Excel 用例约定

相比旧的零散脚本，这里做了几件事：

- 统一了路径解析，直接按仓库结构寻找 `vedio` 和 `voice_test`
- 保留 `voice_test` 的 Excel 列名和音频拼接方式
- 将评估结果稳定写入 `integrated_voice_eval/output/eval_results.xlsx`
- 正确合并服务端返回的分段 WAV 音频，避免直接拼字节导致文件损坏
- 支持命令行覆盖测试集、音频目录、输出文件

## 运行方式

先启动全双工语音对话系统：

```powershell
cd C:\Users\silin\Desktop\audio\testChatBot\vedio
python start.py
```

再运行评估：

```powershell
cd C:\Users\silin\Desktop\audio\integrated_voice_eval
python run_eval.py
```

如果测试集或音频目录不在默认位置，可以覆盖：

```powershell
python run_eval.py `
  --test-case-file C:\path\to\cases.xlsx `
  --audio-input-dir C:\path\to\voice_input_file `
  --pre-wav-path C:\path\to\output_recording.wav `
  --result-file C:\path\to\eval_results.xlsx
```

## 默认约定

- WebSocket 地址：`ws://localhost:8765/ws/{client_id}`
- Excel Sheet：`Sheet2`
- Excel 起始行：`2`
- 兼容的列名：
  - `用例子编号`
  - `音频文件路径`
  - `回复的内容`
  - `识别到的情绪`
  - `回复的情绪`
  - `回复语音保存路径`

## 输出

- 结果表：`integrated_voice_eval/output/eval_results.xlsx`
- 返回语音：`integrated_voice_eval/output/voice_output/`
