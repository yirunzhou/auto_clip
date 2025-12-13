# auto_clip 快速上手指南

auto_clip 帮你把冗长的字幕稿（SRT）或 `.docx` 文档转成可复用的 YouTube 精选片段。上传文件后，可以直接浏览推荐片段并在浏览器中下载或剪辑。DOCX 中的中英文段落都会参与分析；如未启用 DashScope/Qwen，将自动退回到本地 KeyBERT（效果略弱）。

### 你需要准备

- Python 3.11+
- 本地安装 `ffmpeg`（如果你需要在本机剪切视频）
- `yt-dlp`（随 requirements 自动安装）。如果你有自定义的可执行文件，可通过 `YT_DLP_PATH` 指定路径
- 可选但强烈推荐：配置 DashScope/Qwen API Key，以获取更智能的关键词提取能力，需要i云百炼国际版API key (正在寻找替代方案)

### 一次性安装步骤

1. **克隆项目并创建虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **安装依赖**
   ```bash
   pip install pip-tools
   pip-compile requirements.in
   pip install -r requirements.txt
   ```

3. **配置环境变量**

   将 `.env.example` 复制为 `.env`，并根据需要填写值：
   ```bash
   cp .env.example .env
   ```

   如果想使用 Qwen/DashScope 的 LLM 关键词提取，请设置 `DASHSCOPE_API_KEY`（以及可选的 `DASHSCOPE_MODEL` / `DASHSCOPE_ENDPOINT`）。

### 启动 Web 应用

```bash
python web_app.py             # 默认生产模式
# 或者在开发时使用热重载：
flask --app web_app.py --debug run
```

打开浏览器访问 `http://127.0.0.1:5000`：
- **字幕工作流(Transcript workflow)**：上传 `.srt` 或英文 `.docx` 文件，查看自动提取的片段及对应的 YouTube 搜索结果。长文档会分页处理，如看到 “Continue processing” 提示，可按提示继续生成下一批结果。
- **手动工作流(Manual YouTube clips)**：粘贴一组 YouTube 链接，并使用自定义时间码进行下载或剪切。

所有请求都会记录到 `logs/web_app.log`，方便在编辑团队遇到问题时收集堆栈信息。

### 小贴士

- 在 macOS 用 Homebrew 安装 `ffmpeg`（`brew install ffmpeg`）；Windows 用 Chocolatey（`choco install ffmpeg`）；或从 https://ffmpeg.org/ 下载安装包。
- `yt-dlp` 默认使用系统 PATH 或 `YT_DLP_PATH` 指定的路径，无需硬编码虚拟环境里的可执行文件。
- 文档导入目前仅支持 `.docx` 文件；如果是旧的 `.doc`，请先用 Word 或 LibreOffice 转换。中文段落会被保留并推荐使用 DashScope/Qwen 提取关键词，若未配置将退回到本地 KeyBERT；建议上传前删除单独的标题，避免与正文拼接。
- 如果希望在本地运行测试或 CI，请额外安装 `requirements-dev.txt` 中的开发依赖（包含 pytest）。

### 常见问题及解决方法

- **“Warning: LLM keyword search failed; using local KeyBERT.”**  
  出现这个横幅（以及 `logs/web_app.log` 中的对应条目）说明 DashScope/Qwen 调用失败。检查 `.env` 是否配置正确，`DASHSCOPE_API_KEY` 是否已经填写。

- **DashScope 凭据错误**  
  缺失或无效的 Key 会导致 CLI 静默降级到 KeyBERT。查看 `web_app.log`（搜索 `Invalid API-key provided` 或 `LLM keyword extraction unavailable`），或重新检查 `DASHSCOPE_API_KEY` 是否正确。

### 示例视频: [yt 链接](http://youtube.com/watch?v=dYGytHttcJc)

---

# auto_clip quickstart

auto_clip helps you turn long transcripts (SRT) or `.docx` documents into curated YouTube references. Upload the file, skim suggested clips, and optionally download or trim them in the browser. DOCX paragraphs may include Chinese; DashScope/Qwen is recommended for keywords, but the app now falls back to the multilingual KeyBERT model when the LLM isn’t available.

## What you need

- Python 3.11+.
- `ffmpeg` installed locally if you plan to trim clips.
- `yt-dlp` (bundled via `requirements.txt`; override with `YT_DLP_PATH` if needed).
- Optional but recommended: DashScope/Qwen API keys for smarter keyword extraction.

## One-time setup

1. **Clone & create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install pip-tools
   pip-compile requirements.in
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   - Populate `DASHSCOPE_API_KEY` (and optionally `DASHSCOPE_MODEL` / `DASHSCOPE_ENDPOINT`) to enable Qwen/DashScope keyword extraction.

## Start the web app

```bash
python web_app.py            # default production-style server
# or, if you need hot reload while developing:
flask --app web_app.py --debug run
```

Then browse to `http://127.0.0.1:5000`:
- **Transcript workflow**: upload an `.srt` or `.docx` (after basic cleanup) and review the suggested segments + YouTube hits. Long inputs are paginated; click “Continue processing” when prompted to generate the next batch of segments.
- **Manual workflow**: paste a list of YouTube links and download or trim them with custom timecodes.

Every request is logged to `logs/web_app.log`, making it easy to share stack traces when editors report issues.

## Tips

- Install `ffmpeg` via Homebrew (`brew install ffmpeg`), Chocolatey (`choco install ffmpeg`), or grab binaries from https://ffmpeg.org/.
- `yt-dlp` defaults to your PATH or `YT_DLP_PATH`; no need to hardcode the repo’s `venv` path.
- Keep both `requirements.in` (top-level deps) and the compiled `requirements.txt` in version control for reproducible installs.
- Document ingestion currently supports `.docx` inputs only; convert legacy `.doc` files before uploading. Chinese paragraphs are preserved; DashScope/Qwen yields the best keywords, but the multilingual KeyBERT fallback is used automatically if the LLM is unavailable.
- Install `requirements-dev.txt` if you plan to run the pytest suite locally or in CI.

## Common issues & fixes

- **“Warning: LLM keyword search failed; using local KeyBERT.”**  
  This banner (and a matching entry in `logs/web_app.log`) means the DashScope/Qwen call failed. Double-check your `.env` matches `.env.example` and that `DASHSCOPE_API_KEY` is populated.

- **DashScope credential mistakes.**  
  Missing or invalid keys cause the keyword extractor to fall back to KeyBERT silently in the CLI. Check `web_app.log` (look for `Invalid API-key provided` or `LLM keyword extraction unavailable`) or rerun with `DASHSCOPE_API_KEY` set correctly.

## CI & tests

- Install dev dependencies with `pip install -r requirements-dev.txt`.
- Run `pytest` (or `PYTHONPATH=. pytest`) before submitting changes; GitHub Actions (`.github/workflows/tests.yml`) does the same on every PR.

## Video Tutorial: [youtube link](http://youtube.com/watch?v=dYGytHttcJc)
