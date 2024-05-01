import yaml
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import Optional, Union, List


def get_k8s_namespace():
    namespace_file_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    try:
        current_k8s_namespace = open(namespace_file_path).read()
    except:
        current_k8s_namespace = "default"
        print(
            f"Failed to detect current k8s namespace in {namespace_file_path} - falling back to value '{current_k8s_namespace}'."
        )
    return current_k8s_namespace


class AppSettings(BaseSettings):
    """
    Settings object for the UI example app.
    """

    # Allow settings to be overwritten by LLM_UI_<NAME> env vars
    model_config = SettingsConfigDict(env_prefix="llm_ui_")

    # General settings
    hf_model_name: str = Field(
        description="The model to use when constructing the LLM Chat client. This should match the model name running on the vLLM backend",
    )
    backend_url: HttpUrl = Field(
        default_factory=lambda: f"http://llm-backend.{get_k8s_namespace()}.svc"
    )
    page_title: str = Field(default="Large Language Model")
    hf_model_instruction: str = Field(
        default="You are a helpful and cheerful AI assistant. Please respond appropriately."
    )

    # Model settings
    # For available parameters, see https://docs.vllm.ai/en/latest/dev/sampling_params.html
    # which is based on https://platform.openai.com/docs/api-reference/completions/create
    llm_max_tokens: int = Field(default=500)
    llm_temperature: float = Field(default=0.5)
    llm_top_p: float = Field(default=1)
    llm_top_k: float = Field(default=-1)
    llm_presence_penalty: float = Field(default=0, ge=-2, le=2)
    llm_frequency_penalty: float = Field(default=0, ge=-2, le=2)

    # UI theming

    # Variables explicitly passed to gradio.theme.Default()
    # For example:
    # {"primary_hue": "red"}
    theme_params: dict[str, Union[str, List[str]]] = Field(default_factory=dict)
    # Overrides for theme.body_background_fill property
    theme_background_colour: Optional[str] = Field(default=None)
    # Custom page title colour override passed as CSS
    theme_title_colour: Optional[str] = Field(default=None)

    # Method for loading settings file
    @staticmethod
    def load(file_path: str):
        try:
            with open(file_path, "r") as file:
                settings = yaml.safe_load(file)
        except Exception as e:
            print(f"Failed to read config file at: {file_path}\nException was:")
            raise e
        return AppSettings(**settings)
