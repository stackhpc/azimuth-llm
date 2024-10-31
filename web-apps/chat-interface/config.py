import logging
import yaml
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import Optional, Union, List

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


NAMESPACE_FILE_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
def get_k8s_namespace():
    try:
        current_k8s_namespace = open(NAMESPACE_FILE_PATH).read()
        return current_k8s_namespace
    except FileNotFoundError as err:
        return None

def default_backend():
    k8s_ns = get_k8s_namespace()
    if k8s_ns:
        return f"http://llm-backend.{k8s_ns}.svc"
    else:
        logger.warning('Failed to determine k8s namespace from %s - assuming non-kubernetes environment.', NAMESPACE_FILE_PATH)


class AppSettings(BaseSettings):
    """
    Settings object for the UI example app.
    """

    # # Allow settings to be overwritten by LLM_UI_<NAME> env vars
    # model_config = SettingsConfigDict(env_prefix="llm_ui_")

    # General settings
    hf_model_name: str = Field(
        description="The model to use when constructing the LLM Chat client. This should match the model name running on the vLLM backend",
    )
    backend_url: HttpUrl = Field(
        description="The address of the OpenAI compatible API server (either in-cluster or externally hosted)"
    )
    page_title: str = Field(default="Large Language Model")
    page_description: Optional[str] = Field(default=None)
    hf_model_instruction: str = Field(
        default="You are a helpful and cheerful AI assistant. Please respond appropriately."
    )

    # Model settings

    # For available parameters, see https://docs.vllm.ai/en/latest/dev/sampling_params.html
    # which is based on https://platform.openai.com/docs/api-reference/completions/create
    llm_max_tokens: int = Field(default=500)
    llm_temperature: float = Field(default=0)
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
    # Provides arbitrary CSS and JS overrides to the UI,
    # see https://www.gradio.app/guides/custom-CSS-and-JS
    css_overrides: Optional[str] = Field(default=None)
    custom_javascript: Optional[str] = Field(default=None)


    # Method for loading settings from files
    @staticmethod
    def _load_yaml(file_path: str):
        with open(file_path, "r") as file:
            content = yaml.safe_load(file) or {}
            return content

    @staticmethod
    def load():
        defaults = AppSettings._load_yaml('./defaults.yml')
        overrides = {}
        try:
            overrides = AppSettings._load_yaml('/etc/web-app/overrides.yml')
        except FileNotFoundError:
            pass
        settings = {**defaults, **overrides}
        # Sanity checks on settings
        if 'backend_url' not in settings:
            in_cluster_backend = default_backend()
            if not in_cluster_backend:
                raise Exception('Backend URL must be provided in settings when running this app outside of Kubernetes')
            settings['backend_url'] = in_cluster_backend
        return AppSettings(**settings)
