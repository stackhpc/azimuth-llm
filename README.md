# Azimuth LLM

This repository contains a Helm chart for deploying Large Language Models (LLMs) on Kubernetes. It is developed primarily for use as a pre-packaged application within [Azimuth](https://www.stackhpc.com/azimuth-introduction.html) but is structured such that it can, in principle, be deployed on any Kubernetes cluster with at least 1 GPU node.

# Deployment

## Azimuth

This app ~~is~~ will soon be provided as part of a standard deployment Azimuth so no specific steps are required to use this app other than access to an up to date Azimuth deployment.

## Manual Installation

To set up the Helm repository and manually install this chart on an arbitrary Kubernetes cluster, run

```
helm repo add <chosen-repo-name> https://stackhpc.github.io/azimuth-llm/
helm repo update
helm install <installation-name> <chosen-repo-name>/azimuth-llm --version <version>
```

where version is the full published version for the specified commit (e.g. `0.1.0-dev.0.main.125`). To see the latest published version, see [here](https://github.com/stackhpc/azimuth-llm/tree/gh-pages).

### Customisation

The `chart/values.yaml` file documents the various customisation options which are available. In order to access the LLM from outside the Kubernetes cluster, the API and/or UI service types may be changed to
```
api:
  service:
    type: LoadBalancer
ui:
  service:
    type: LoadBalancer
```

***Warning*** - Exposing the services in this way provides no authentication mechanism and anyone with access to the load balancer IPs will be able to query the language model. In the Azimuth deployment case, authentication is provided via the standard Azimuth identity provider mechanisms and the authenticated services are exposed via [Zenith](https://github.com/stackhpc/zenith).


## Tested Models

The following is a non-exhaustive list of models which have been tested with this app:
- [Llama 2 7B chat](https://huggingface.co/meta-llama/Llama-2-7b-chat-hf)
- [AWQ Quantized Llama 2 70B](https://huggingface.co/TheBloke/Llama-2-70B-Chat-AWQ)
- [Magicoder 6.7B](https://huggingface.co/ise-uiuc/Magicoder-S-DS-6.7B)

Due to the combination of [components](##Components) used in this app, some Huggingface models may not work as expected (usually due to the way in which LangChain formats the prompt messages). Any errors when using new model The logs for the API pod will usually provide more information on failed requests.


## Components

*TO-DO*
