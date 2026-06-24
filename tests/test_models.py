from aicoder.agent.models import list_models, get_model_info, create_chat_model, MODEL_REGISTRY


class TestModelRegistry:
    def test_list_models_returns_all_registered(self):
        models = list_models()
        assert "deepseek-chat" in models
        assert "deepseek-reasoner" in models
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models

    def test_get_model_info_known(self):
        info = get_model_info("deepseek-chat")
        assert info is not None
        assert info["provider"] == "deepseek"
        assert info["model"] == "deepseek-chat"

    def test_get_model_info_unknown(self):
        assert get_model_info("nonexistent") is None

    def test_create_deepseek_model(self):
        model = create_chat_model("deepseek-chat", api_key="test-key", temperature=0.0)
        assert model.model_name == "deepseek-chat"
        assert model.openai_api_base == "https://api.deepseek.com"

    def test_create_gpt_model(self):
        model = create_chat_model("gpt-4o-mini", api_key="test-key", temperature=0.0)
        assert model.model_name == "gpt-4o-mini"

    def test_unknown_model_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown model"):
            create_chat_model("bad-model")
