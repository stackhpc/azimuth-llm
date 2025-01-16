# Azimuth LLM

This repository contains a set of Helm charts for deploying Large Language Models (LLMs) on Kubernetes. It is developed primarily for use as a set of pre-packaged applications within [Azimuth](https://www.stackhpc.com/azimuth-introduction.html) but is structured such that the charts can, in principle, be deployed on any Kubernetes cluster with at least 1 GPU node.

## Azimuth App

This primary LLM chat app is provided as part of a standard deployment Azimuth, so no specific steps are required to use this app other than access to an up-to-date Azimuth deployment.

## Manual Deployment

Alternatively, to set up the Helm repository and manually install the LLM chat interface chart on an existing Kubernetes cluster, run

```
helm repo add <chosen-repo-name> https://stackhpc.github.io/azimuth-llm/
helm repo update
helm install <installation-name> <chosen-repo-name>/azimuth-llm-chat
```

This will install the latest stable [release](https://github.com/stackhpc/azimuth-llm/releases) of the application.

## Chart Structure

Under the charts directory, there is a base [azimuth-llm](./charts/azimuth-llm) Helm chart which uses vLLM to deploy models from Huggingface. The [azimuth-chat](charts/azimuth-chat) and [azimuth-image-analysis](charts/azimuth-image-analysis) are wrapper charts which add different Gradio web interfaces for interacting with the deployed LLM.

### Customisation

The `charts/azimuth-llm/values.yaml` file documents the various customisation options which are available. In order to access the LLM from outside the Kubernetes cluster, the API and/or UI service types may be changed to
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

[!WARNING] Exposing the services in this way provides no authentication mechanism and anyone with access to the load balancer IPs will be able to query the language model. It is up to you to secure the running service as appropriate for your use case. In contrast, when deployed via Azimuth, authentication is provided via the standard Azimuth Identity Provider mechanisms and the authenticated services are exposed via [Zenith](https://github.com/stackhpc/zenith).

The both the web-based interface and the backend OpenAI-compatible vLLM API server can also optionally be exposed using [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/). See the `ingress` section in `values.yml` for available config options.

When deploying the chat or image-analysis wrapper charts, all configuration options must be nested under the `azimuth-llm` heading ([example](https://github.com/stackhpc/azimuth-llm/blob/main/charts/azimuth-chat/values.yaml#L1)) due to the way that Helm passes values between [parent charts and sub-charts](https://helm.sh/docs/chart_template_guide/subcharts_and_globals/#overriding-values-from-a-parent-chart).

## Tested Models

The application uses [vLLM](https://docs.vllm.ai/en/latest/index.html) for model serving, therefore any of the vLLM [supported models](https://docs.vllm.ai/en/latest/models/supported_models.html) should work. Since vLLM pulls the model files directly from [HuggingFace](https://huggingface.co/models) it is likely that some other models will also be compatible with vLLM but mileage may vary between models and model architectures. If a model is incompatible with vLLM then the API pod will likely enter a `CrashLoopBackoff` state and any relevant error information will be found in the API pod logs. These logs can be viewed with

```
kubectl (-n <helm-release-namespace>) logs deploy/<helm-release-name>-api
```

If you suspect that a given error is not caused by the upstream vLLM version and is instead a problem with this Helm chart then please [open an issue](https://github.com/stackhpc/azimuth-llm/issues).

## Monitoring

The LLM chart integrates with [kube-prometheus-stack](https://artifacthub.io/packages/helm/prometheus-community/kube-prometheus-stack) by creating a `ServiceMonitor` resource and installing two custom Grafana dashboard as Kubernetes `ConfigMap`s. If the target cluster has an existing `kube-prometheus-stack` deployment which is appropriately configured to watch all namespaces for new Grafana dashboards, the LLM dashboards will automatically appear in Grafana's dashboard list.

To disable the monitoring integrations, set the `api.monitoring.enabled` value to `false`.

## Components

The Helm chart consists of the following components:
- A backend web API which runs [vLLM](https://github.com/vllm-project/vllm)'s [OpenAI compatible web server](https://docs.vllm.ai/en/stable/getting_started/quickstart.html#openai-compatible-server).

- A choice of frontend web-apps built using [Gradio](https://www.gradio.app) (see [web-apps](./web-apps/)). Each web interface is available as a pre-built container image [hosted on ghcr.io](https://github.com/orgs/stackhpc/packages?repo_name=azimuth-llm) and be configured for each Helm release by changing the `ui.image` section of the chart values.

<!-- ## Development

TODO: Update this

The GitHub repository includes a [tilt](https://tilt.dev) file for easier development. After installing tilt locally, simply run `tilt up` from the repo root to get started with development. This will trigger the following:

- Install the backend API components of the Helm chart on the remote k8s cluster specified by your current k8s context.

- Create a port-forward from the remote cluster to `localhost:8080`

- Create a local `tilt-dev-venv` in the repo root containing the required Python dependencies to run the frontend web app locally.

- Launch the frontend web app locally on `127.0.0.1:7860`, configured to use `localhost:8080` as the backend API

- Watch all components and only reload the minimal set of components needed when a file in the repo changes (e.g. modifying `chart/web-app/app.py` will restart the local web app instance only) -->

<!-- ## Adding a new web interface

TODO: Write these docs... -->
