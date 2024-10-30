#####
# Shared utility functions and models for re-use by multiple web apps
#####

import logging
import pathlib
import yaml
from typing import Annotated
from pydantic import BaseModel, ConfigDict, PositiveInt, Field

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LLMParams(BaseModel):
    """
    Parameters for vLLM API requests. For details see
    https://platform.openai.com/docs/api-reference/chat/create
    https://docs.vllm.ai/en/stable/serving/openai_compatible_server.html#extra-parameters
    """

    max_tokens: PositiveInt | None
    temperature: Annotated[float, Field(ge=0, le=2)] | None
    top_p: Annotated[float, Field(gt=0, le=1)] | None
    top_k: Annotated[int, Field(ge=-1)] | None
    frequency_penalty: Annotated[float, Field(ge=-2, le=2)] | None
    presence_penalty: Annotated[float, Field(ge=0 - 2, le=2)] | None
    # Make sure we can't smuggle in extra request params / typos
    model_config = ConfigDict(extra="forbid")


NAMESPACE_FILE_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"


def get_k8s_namespace():
    try:
        current_k8s_namespace = open(NAMESPACE_FILE_PATH).read()
        return current_k8s_namespace
    except FileNotFoundError as err:
        return None


def api_address_in_cluster():
    k8s_ns = get_k8s_namespace()
    if k8s_ns:
        return f"http://llm-backend.{k8s_ns}.svc"
    else:
        logger.warning(
            "Failed to determine k8s namespace from %s - assuming non-kubernetes environment.",
            NAMESPACE_FILE_PATH,
        )


# Method for loading settings from files
def load_yaml(file_path: str) -> dict:
    with open(file_path, "r") as file:
        content = yaml.safe_load(file) or {}
        return content


def load_settings() -> dict:

    defaults = load_yaml("./defaults.yml")
    overrides = {}
    # Path must match the one used in the Helm chart's
    # app-config-map.yml template
    path = pathlib.Path("/etc/web-app/overrides.yml")
    if path.exists():
        overrides = load_yaml(path)
    else:
        # Allow local overrides for dev/testing
        path = pathlib.Path("./overrides.yml")
        if path.exists():
            overrides = load_yaml(path)

    # Sanity checks on settings
    unused_overrides = [k for k in overrides.keys() if k not in defaults.keys()]
    if unused_overrides:
        logger.warning(
            f"Overrides {unused_overrides} not part of default settings so may be ignored."
            "Please check for typos"
        )
    settings = {**defaults, **overrides}
    if "backend_url" not in settings or not settings["backend_url"]:
        # Try to detect in-cluster address
        in_cluster_backend = api_address_in_cluster()
        if not in_cluster_backend:
            raise Exception(
                "Backend URL must be provided in settings when running outside of Kubernetes."
            )
        settings["backend_url"] = in_cluster_backend
    return settings
