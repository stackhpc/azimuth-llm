from pydantic import Field, HttpUrl
from pydantic.alias_generators import to_camel
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml

from typing import Optional

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
    backend_url: HttpUrl = Field(default_factory=lambda: f"http://llm-backend.{get_k8s_namespace()}.svc")
    page_title: str = "Large Language Model"

    # Prompt settings
    prompt_template: str = Field(
        description="The template to use for requests to the backend model. If present, the '\{context\}' placeholder will be replaced by the conversation history of the current session. In order for the frontend to correctly filter out context from the displayed text, the context placeholder must not appear on the final line of the prompt template.",
    )
    # The following settings are only used if {context} used in prompt template
    include_past_user_messages_in_context: bool = True
    include_past_system_responses_in_context: bool = True
    user_context_template: str = Field(
        default="<<USER>>\n{user_input}\n<</USER>>\n",
        description="The template string to use for including user messages in the prompt context sent to backend. The '\{user_input\}' placeholder will be replaced by the the user's messages. (Only applies if '\{context\}' is present in prompt_template)",
    )
    system_context_template: str = Field(
        default="<SYS>>{system_response}\n<</SYS>>\n",
        description="The template string to use for if user messages are included in context sent to backend. The '\{system_response\}' placeholder will be replaced by the system's response to each user message. (Only applies if '\{context\}' is present in prompt_template)",
    )

    # Model settings
    llm_params: dict[str, float] = {}
    llm_max_tokens: int = 1000

    # UI theming
    # Variables explicitly passed to gradio.theme.Default()
    theme_primary_hue: str = Field(default="orange")
    theme_secondary_hue: str = Field(default="blue")
    theme_neutral_hue: str = Field(default="gray")
    # Overrides for theme.body_background_fill property
    theme_background_colour: Optional[str] = None
    # Custom page title colour override passed as CSS
    theme_title_colour: Optional[str] = None

    @staticmethod
    def load(file_path: str):
        try:
            with open(file_path, "r") as file:
                settings = yaml.safe_load(file)
        except Exception as e:
            print(f"Failed to read config file at: {file_path}\nException was:")
            raise e
        return AppSettings(**settings)
