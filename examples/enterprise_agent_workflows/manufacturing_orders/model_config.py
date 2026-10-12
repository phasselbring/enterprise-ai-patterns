"""Provider selection without credentials in source control."""
import os

DEFAULT_MODELS = {
    'openai': 'openai:gpt-4.1-mini',
    'claude': 'anthropic:claude-sonnet-4-5',
    'gemini': 'google_genai:gemini-2.5-flash',
}
KEY_ENV = {
    'openai': 'OPENAI_API_KEY',
    'claude': 'ANTHROPIC_API_KEY',
    'gemini': 'GOOGLE_API_KEY',
}


def model_for(provider: str) -> str:
    provider = provider.lower().strip()
    if provider not in DEFAULT_MODELS:
        raise ValueError(f'Unknown provider {provider!r}; choose: {", ".join(DEFAULT_MODELS)}')
    if not os.environ.get(KEY_ENV[provider]):
        raise RuntimeError(f'{KEY_ENV[provider]} is not set for {provider}')
    # Provider-specific overrides avoid accidentally invoking a different provider.
    return os.getenv(f'{provider.upper()}_AGENT_MODEL') or DEFAULT_MODELS[provider]
