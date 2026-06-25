import os
import httpx
from langchain_openai import ChatOpenAI

# Monkey-patch httpx to filter non-ASCII headers (prompt_toolkit causes Unicode leak)
_original_headers_init = httpx.Headers.__init__

def _safe_headers_init(self, headers=None, encoding=None):
    try:
        if headers is not None:
            if isinstance(headers, dict):
                clean = {}
                for k, v in headers.items():
                    if isinstance(v, str):
                        v = v.encode("ascii", errors="replace").decode("ascii")
                    clean[k] = v
                headers = clean
            elif isinstance(headers, (list, tuple)):
                clean = []
                for item in headers:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        k, v = item
                        if isinstance(v, str):
                            v = v.encode("ascii", errors="replace").decode("ascii")
                        clean.append((k, v))
                    elif isinstance(item, (list, tuple)):
                        clean.append(tuple(item[:2]))
                    else:
                        clean.append(item)
                headers = clean
    except Exception:
        pass
    return _original_headers_init(self, headers, encoding=encoding)

httpx.Headers.__init__ = _safe_headers_init

# Try optional imports for other providers
try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

MODEL_REGISTRY = {
    "deepseek-chat": {
        "display": "DeepSeek Chat",
        "provider": "deepseek",
        "model": "deepseek-chat",
        "api_base": "https://api.deepseek.com",
        "env_key": "DEEPSEEK_API_KEY",
        "vision": False,
    },
    "deepseek-reasoner": {
        "display": "DeepSeek Reasoner",
        "provider": "deepseek",
        "model": "deepseek-reasoner",
        "api_base": "https://api.deepseek.com",
        "env_key": "DEEPSEEK_API_KEY",
        "vision": False,
    },
    "deepseek-vl2": {
        "display": "DeepSeek VL2 (beta)",
        "provider": "deepseek",
        "model": "deepseek-vl2",
        "api_base": "https://api.deepseek.com/beta",
        "env_key": "DEEPSEEK_API_KEY",
        "vision": False,
        "note": "Does not support standard image_url format. Use glm-4v or gpt-4o.",
    },
    "gpt-4o": {
        "display": "GPT-4o",
        "provider": "openai",
        "model": "gpt-4o",
        "api_base": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "vision": True,
    },
    "gpt-4o-mini": {
        "display": "GPT-4o Mini",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_base": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "vision": True,
    },
    "glm-4v": {
        "display": "GLM-4V",
        "provider": "zhipu",
        "model": "glm-4v",
        "api_base": "https://open.bigmodel.cn/api/paas/v4/",
        "env_key": "ZHIPUAI_API_KEY",
        "vision": True,
    },
    "glm-4v-flash": {
        "display": "GLM-4V Flash",
        "provider": "zhipu",
        "model": "glm-4v-flash",
        "api_base": "https://open.bigmodel.cn/api/paas/v4/",
        "env_key": "ZHIPUAI_API_KEY",
        "vision": True,
    },
}


def supports_vision(model_name: str) -> bool:
    info = get_model_info(model_name)
    return info.get("vision", False) if info else False


def find_vision_model(preferred: str = "gpt-4o") -> str | None:
    """Find an available vision model, preferring the given one."""
    if preferred in MODEL_REGISTRY and MODEL_REGISTRY[preferred].get("vision"):
        return preferred
    for name, info in MODEL_REGISTRY.items():
        if info.get("vision"):
            return name
    return None


def list_models() -> list[str]:
    return list(MODEL_REGISTRY.keys())


def get_model_info(name: str) -> dict | None:
    return MODEL_REGISTRY.get(name)


def create_chat_model(model_name: str, api_key: str = "", temperature: float = 0.0):
    info = get_model_info(model_name)
    if not info:
        raise ValueError(f"Unknown model: {model_name}. Available: {list_models()}")

    key = os.environ.get(info["env_key"], "") or api_key
    if info.get("vision"):
        import sys
        print(f"[vision] model={model_name}, env_key={info['env_key']}, key_present={bool(key)}, key_len={len(key) if key else 0}", file=sys.stderr)

    if info["provider"] in ("deepseek", "openai", "zhipu"):
        return ChatOpenAI(
            model=info["model"],
            api_key=key,
            base_url=info["api_base"],
            temperature=temperature,
        )
    elif info["provider"] == "anthropic":
        if ChatAnthropic is None:
            raise ImportError("langchain-anthropic is required for Anthropic models")
        return ChatAnthropic(
            model=info["model"],
            api_key=key,
            base_url=info.get("api_base"),
            temperature=temperature,
        )
    raise ValueError(f"Unknown provider: {info['provider']}")
