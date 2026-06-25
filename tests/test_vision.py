"""Tests for vision module — all runnable without REPL."""
import os
import base64
from pathlib import Path
import pytest
from aicoder.agent.vision import ImageAttachment, pick_vision_model, describe_model


class TestImageAttachment:
    def test_build_basic_message(self):
        img = ImageAttachment(b64="aGVsbG8=", mime="image/png", source="/tmp/x.png")
        msg = img.build_message("描述一下")
        assert msg["role"] == "user"
        content = msg["content"]
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "描述一下"
        assert content[1]["type"] == "image_url"
        assert "base64,aGVsbG8=" in content[1]["image_url"]["url"]

    def test_default_text_when_empty(self):
        img = ImageAttachment(b64="x", mime="image/jpeg")
        msg = img.build_message("")
        assert msg["content"][0]["text"] == "Analyze this image"

    def test_size_kb(self):
        # 2000 chars = ~2KB base64
        img = ImageAttachment(b64="a" * 2000, mime="image/png")
        assert img.size_kb == 1  # 2000 // 1024 = 1


class TestReadImage:
    def test_read_valid_png(self, tmp_path):
        from aicoder.agent.images import read_image
        p = tmp_path / "test.png"
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )
        p.write_bytes(png)
        b64, mime = read_image(p)
        assert mime == "image/png"
        assert len(b64) > 0

    def test_read_invalid_format(self, tmp_path):
        from aicoder.agent.images import read_image
        from aicoder.agent.images import ImageError
        p = tmp_path / "test.bmp"
        p.write_text("fake")
        with pytest.raises(ImageError):
            read_image(p)

    def test_read_missing_file(self, tmp_path):
        from aicoder.agent.images import read_image
        from aicoder.agent.images import ImageError
        with pytest.raises(ImageError):
            read_image(tmp_path / "nonexistent.png")


class TestModelSelection:
    def test_pick_vision_with_zhipu_key(self, monkeypatch):
        monkeypatch.setenv("ZHIPUAI_API_KEY", "test-key")
        from aicoder.agent.vision import pick_vision_model
        model = pick_vision_model()
        assert model == "glm-4v"

    def test_pick_vision_with_openai_key(self, monkeypatch):
        monkeypatch.delenv("ZHIPUAI_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        from aicoder.agent.vision import pick_vision_model
        model = pick_vision_model()
        assert model == "gpt-4o"

    def test_pick_vision_no_key(self, monkeypatch):
        monkeypatch.delenv("ZHIPUAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from aicoder.agent.vision import pick_vision_model
        model = pick_vision_model()
        assert model is None

    def test_supports_vision(self):
        from aicoder.agent.models import supports_vision
        assert supports_vision("glm-4v") is True
        assert supports_vision("deepseek-chat") is False

    def test_describe_model(self):
        from aicoder.agent.vision import describe_model
        assert describe_model("glm-4v") == "GLM-4V"
        assert describe_model("unknown") == "unknown"
