"""Simple Flask app to run the auto_clip search pipeline from a browser."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from flask import Flask, render_template_string, request

from auto_clip_lib.workflow import run_metadata_workflow


app = Flask(__name__)


INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>auto_clip demo</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; }
      form { margin-bottom: 2rem; }
      .segment { border: 1px solid #ddd; padding: 1rem; margin-bottom: 1rem; border-radius: 6px; }
      .segment h3 { margin: 0 0 0.5rem 0; }
      .error { color: #b00020; margin-bottom: 1rem; }
      ul { padding-left: 1.2rem; }
      .status { margin-top: 1rem; color: #555; }
  </style>
  </head>
  <body>
    <h1>auto_clip: Metadata Search</h1>
    <p>Upload an .srt file to run the keyword + YouTube search pipeline and review the results.</p>
    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}
    <form method="post" enctype="multipart/form-data" data-loading-target="upload-status" data-loading-text="Processing transcript..." data-loading-label="Processing...">
      <label for="srt_file">Select SRT file:</label>
      <input type="file" id="srt_file" name="srt_file" accept=".srt" required />
      <button type="submit">Search</button>
    </form>
    <div id="upload-status" class="status"></div>

    {% if segments %}
      <h2>Results</h2>
      {% if metadata_path %}
        <p><strong>Metadata JSON:</strong> {{ metadata_path }}</p>
      {% endif %}
      {% for seg in segments %}
        {% if seg.video_results %}
          <div class="segment">
            <h3>Segment {{ loop.index }}</h3>
            <p><strong>Time:</strong> {{ "%.2f"|format(seg.start) }}s → {{ "%.2f"|format(seg.end) }}s</p>
            <p>{{ seg.text }}</p>
            <p><strong>Queries tried:</strong> {{ seg.queries_tried|join(', ') }}</p>
            <ul>
              {% for video in seg.video_results %}
                <li>
                  <a href="{{ video.url }}" target="_blank" rel="noopener">{{ video.title or video.id }}</a>
                  {% if video.channel %}- {{ video.channel }}{% endif %}
                </li>
              {% endfor %}
            </ul>
          </div>
        {% endif %}
      {% endfor %}
    {% elif segments is not none %}
      <p>No YouTube results found for this transcript.</p>
    {% endif %}
    <script>
      document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('form[data-loading-target]').forEach(function (form) {
          form.addEventListener('submit', function () {
            var btn = form.querySelector('button[type="submit"]');
            if (btn) {
              btn.disabled = true;
              var label = form.getAttribute('data-loading-label') || 'Processing...';
              btn.dataset.originalText = btn.textContent;
              btn.textContent = label;
            }
            var targetId = form.getAttribute('data-loading-target');
            if (targetId) {
              var el = document.getElementById(targetId);
              if (el) {
                el.textContent = form.getAttribute('data-loading-text') || 'Working...';
              }
            }
          }, { once: true });
        });
      });
    </script>
  </body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    segments = None
    metadata_path = None

    if request.method == "POST":
        upload = request.files.get("srt_file")
        if not upload or upload.filename == "":
            error = "Please choose an SRT file to upload."
        else:
            suffix = Path(upload.filename).suffix or ".srt"
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    temp_path = Path(tmp.name)
                    upload.save(str(temp_path))
                output_prefix = Path(upload.filename).stem or "upload"
                (
                    _segments,
                    _output_dir,
                    metadata_file,
                    _,
                ) = run_metadata_workflow(
                    str(temp_path),
                    log_func=None,
                    create_trimmed_dir=False,
                    output_prefix=output_prefix,
                )
                metadata_path = str(metadata_file)
                with metadata_file.open() as f:
                    segments = json.load(f)
            except Exception as exc:  # pragma: no cover - run-time diagnostics
                error = f"Failed to process file: {exc}"
                segments = None
                metadata_path = None
            finally:
                if "temp_path" in locals():
                    temp_path.unlink(missing_ok=True)

    return render_template_string(
        INDEX_TEMPLATE, error=error, segments=segments, metadata_path=metadata_path
    )


if __name__ == "__main__":
    app.run(debug=True)
