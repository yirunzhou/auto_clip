# auto_clip quickstart

auto_clip helps you turn long transcripts into curated YouTube references. Upload an `.srt`, skim the suggested clips, and (optionally) download or trim them straight from the browser.

## What you need

- Python 3.11+.
- `ffmpeg` on your machine if you plan to trim clips.
- `yt-dlp` (installed automatically with our requirements). Set `YT_DLP_PATH` if you use a custom binary.
- Optional but highly recommended: DashScope/Qwen API keys for smarter keyword extraction.

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

   Copy `.env.example` to `.env` and fill in the values that apply:
   ```bash
   cp .env.example .env
   ```
   - Set `DASHSCOPE_API_KEY` (and optionally `DASHSCOPE_MODEL` / `DASHSCOPE_ENDPOINT`) if you want LLM-powered keyword extraction via Qwen/DashScope.

## Start the web app

```bash
python web_app.py            # default production-style server
# or, if you need hot reload while developing:
flask --app web_app.py --debug run
```

Then browse to `http://127.0.0.1:5000`:
- **Transcript workflow**: upload an `.srt` and review the suggested segments + YouTube hits.
- **Manual workflow**: paste a list of YouTube links and download or trim them with custom timecodes.

Every request is logged to `logs/web_app.log`, making it easy to share stack traces when editors report issues.

## Tips

- Install `ffmpeg` via Homebrew (`brew install ffmpeg`), Chocolatey (`choco install ffmpeg`), or grab binaries from https://ffmpeg.org/.
- `yt-dlp` defaults to your PATH or `YT_DLP_PATH`; no need to hardcode the repo’s `venv` path.
- Keep both `requirements.in` (top-level deps) and the compiled `requirements.txt` in version control for reproducible installs.

## Common issues & fixes

- **“Warning: LLM keyword search failed; using local KeyBERT.”**  
  This banner (and a matching entry in `logs/web_app.log`) means the DashScope/Qwen call failed. Double-check your `.env` matches `.env.example` and that `DASHSCOPE_API_KEY` is populated.

- **DashScope credential mistakes.**  
  Missing or invalid keys cause the keyword extractor to fall back to KeyBERT silently in the CLI. Check `web_app.log` (look for `Invalid API-key provided` or `LLM keyword extraction unavailable`) or rerun with `DASHSCOPE_API_KEY` set correctly.

## auto_clip 快速上手指南

auto_clip 帮你把冗长的字幕稿（SRT）自动转成可复用的 YouTube 精选片段。上传 `.srt` 后，你可以直接浏览推荐的关键片段，并可在浏览器中下载或剪辑视频。

### 你需要准备

- Python 3.11+
- 本地安装 `ffmpeg`（如果你需要在本机剪辑视频）
- `yt-dlp`（随 requirements 自动安装）。如果你有自定义的可执行文件，可通过 `YT_DLP_PATH` 指定路径
- 可选但强烈推荐：配置 DashScope/Qwen API Key，以获取更智能的关键词提取能力

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
- **字幕工作流**：上传 `.srt` 文件，查看自动提取的片段及对应的 YouTube 搜索结果。
- **手动工作流**：粘贴一组 YouTube 链接，并使用自定义时间码进行下载或剪辑。

所有请求都会记录到 `logs/web_app.log`，方便在编辑团队遇到问题时收集堆栈信息。

### 小贴士

- 在 macOS 用 Homebrew 安装 `ffmpeg`（`brew install ffmpeg`）；Windows 用 Chocolatey（`choco install ffmpeg`）；或从 https://ffmpeg.org/ 下载安装包。
- `yt-dlp` 默认使用系统 PATH 或 `YT_DLP_PATH` 指定的路径，无需硬编码虚拟环境里的可执行文件。
- 请同时把 `requirements.in`（顶层依赖）和编译后的 `requirements.txt` 纳入版本控制，以确保可重复安装。

### 常见问题及解决方法

- **“Warning: LLM keyword search failed; using local KeyBERT.”**  
  出现这个横幅（以及 `logs/web_app.log` 中的对应条目）说明 DashScope/Qwen 调用失败。检查 `.env` 是否配置正确，`DASHSCOPE_API_KEY` 是否已经填写。

- **DashScope 凭据错误**  
  缺失或无效的 Key 会导致 CLI 静默降级到 KeyBERT。查看 `web_app.log`（搜索 `Invalid API-key provided` 或 `LLM keyword extraction unavailable`），或重新检查 `DASHSCOPE_API_KEY` 是否正确。
