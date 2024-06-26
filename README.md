# Azimuth LLM

This repository contains a Helm chart for deploying Large Language Models (LLMs) on Kubernetes. It is developed primarily for use as a pre-packaged application within [Azimuth](https://www.stackhpc.com/azimuth-introduction.html) but is structured such that it can, in principle, be deployed on any Kubernetes cluster with at least 1 GPU node.

## Azimuth App

This app is provided as part of a standard deployment Azimuth, so no specific steps are required to use this app other than access to an up-to-date Azimuth deployment.

## Manual Deployment

Alternatively, to set up the Helm repository and manually install this chart on an existing Kubernetes cluster, run

```
helm repo add <chosen-repo-name> https://stackhpc.github.io/azimuth-llm/
helm repo update
helm install <installation-name> <chosen-repo-name>/azimuth-llm --version <version>
```

where `version` is the full name of the published version for the specified commit (e.g. `0.1.0-dev.0.main.125`). To see the latest published version, see [this page](https://github.com/stackhpc/azimuth-llm/tree/gh-pages).

### Customisation

The `chart/values.yaml` file documents the various customisation options which are available. In order to access the LLM from outside the Kubernetes cluster, the API and/or UI service types may be changed to
```
api:
  service:
    type: LoadBalancer
    zenith:
      enabled: false
ui:
  service:
    type: LoadBalancer
    zenith:
      enabled: false
```

***Warning*** - Exposing the services in this way provides no authentication mechanism and anyone with access to the load balancer IPs will be able to query the language model. It is up to you to secure the running service in your own way. In contrast, when deploying via Azimuth, authentication is provided via the standard Azimuth Identity Provider mechanisms and the authenticated services are exposed via [Zenith](https://github.com/stackhpc/zenith).

The UI can also optionally be exposed using a Kubernetes Ingress resource. See the `ui.ingress` section in `values.yml` for available config options.

## Tested Models

The following is a non-exhaustive list of models which have been tested with this app:
- [Llama 2 7B chat](https://huggingface.co/meta-llama/Llama-2-7b-chat-hf)
- [AWQ Quantized Llama 2 70B](https://huggingface.co/TheBloke/Llama-2-70B-Chat-AWQ)
- [Magicoder 6.7B](https://huggingface.co/ise-uiuc/Magicoder-S-DS-6.7B)
- [Mistral 7B Instruct v0.2](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2)
- [WizardCoder Python 34B](https://huggingface.co/WizardLM/WizardCoder-Python-34B-V1.0)
- [AWQ Quantized Mixtral 8x7B Instruct v0.1](https://huggingface.co/TheBloke/Mixtral-8x7B-Instruct-v0.1-AWQ)

Due to the combination of [components](##Components) used in this app, some HuggingFace models may not work as expected (usually due to the way in which LangChain formats the prompt messages). Any errors when using a new model will appear in the logs for either the web-app pod or the backend API pod. Please open an issue if you would like explicit support for a specific model that is not in the above list.

## Monitoring

The LLM chart integrates with [kube-prometheus-stack](https://artifacthub.io/packages/helm/prometheus-community/kube-prometheus-stack) by creating a `ServiceMonitor` resource and installing a custom Grafana dashboard as a Kubernetes `ConfigMap`. If the target cluster has an existing `kube-prometheus-stack` deployment which is appropriately configured to watch all namespaces for new Grafana dashboards, the custom LLM dashboard provided here will automatically picked up by Grafana. It will appear in the Grafana dashboard list with the name 'LLM dashboard'.

To disable the monitoring integrations, set the `api.monitoring.enabled` value to `false`.

## Components

The Helm chart consists of the following components:
- A backend web API which runs [vLLM](https://github.com/vllm-project/vllm)'s [OpenAI compatible web server](https://docs.vllm.ai/en/latest/getting_started/quickstart.html#openai-compatible-server).

- A frontend web-app built using [Gradio](https://www.gradio.app) and [LangChain](https://www.langchain.com). The web app source code can be found in `chart/web-app` and gets written to a ConfigMap during the chart build and is then mounted into the UI pod and executed as the entry point for the UI docker image (built from `images/ui-base/Dockerfile`).

- A [stakater/Reloader](https://github.com/stakater/Reloader) instance which monitors the web-app ConfigMap for changes and restarts the frontend when the app code changes (i.e. whenever the Helm values are updated).

## Development

The GitHub repository includes a [tilt](https://tilt.dev) file for easier development. After installing tilt locally, simply run `tilt up` from the repo root to get started with development. This will trigger the following:

- Install the backend API components of the Helm chart on the remote k8s cluster specified by your current k8s context.

- Create a port-forward from the remote cluster to `localhost:8080`

- Create a local `tilt-dev-venv` in the repo root containing the required Python dependencies to run the frontend web app locally.

- Launch the frontend web app locally on `127.0.0.1:7860`, configured to use `localhost:8080` as the backend API

- Watch all components and only reload the minimal set of components needed when a file in the repo changes (e.g. modifying `chart/web-app/app.py` will restart the local web app instance only)