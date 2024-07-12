# Toggles whether UI should be run locally using gradio hot-reloading
# or should be included in the remote Helm install
run_ui_locally = os.getenv("AZIMUTH_LLM_TILT_LOCAL_UI", True)

# Allow non-local contexts
allow_k8s_contexts(k8s_context())

# TODO: Include image builds in tilt up
# docker_build("images/ui-base/")

chart_yaml = helm(
    "chart/",
    values="dev-values.yml",
    # Enable/disable remote UI install depending on if we're running it locally
    set=[
        "ui.enabled={}".format(str(not run_ui_locally).lower())
    ],
)
k8s_yaml(chart_yaml)

# Parse LLM name from templated deployment
api_deployment, _ = filter_yaml(chart_yaml, kind='Deployment', name='chart-api')
hf_model = decode_yaml(api_deployment)['spec']['template']['spec']['containers'][0]['args'][1]

if not run_ui_locally:
    # Port-forward web app to localhost:8080
    k8s_resource("chart-ui", port_forwards="8080:7680")

# Port forward backend UI to localhost:8081 for local web app development
k8s_resource("chart-api", port_forwards="8081:8000")

if run_ui_locally:
    venv_name = "tilt-dev-venv"
    requirements = "images/ui-base/requirements.txt"

    # Ensure venv exists and matches requirements.txt
    local_resource(
        name="gradio-app-venv",
        deps=[requirements],
        cmd=" && ".join([
            "([[ -d {} ]] || python3.11 -m venv {})".format(venv_name, venv_name),
            "source {}/bin/activate".format(venv_name),
            "pip install -r {}".format(requirements),
        ])
    )

    # Run web app locally
    local_resource(
        name="gradio-app",
        deps=["chart/web-app/"],
        resource_deps=["gradio-app-venv"],
        serve_cmd=" && ".join([
            "source {}/bin/activate".format(venv_name),
            "cd chart/web-app",
            "python3 app.py {} localhost".format(hf_model),
        ])
    )
