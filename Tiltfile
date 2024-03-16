# Toggles whether UI should be run locally using gradio hot-reloading
# or should be included in the remote Helm install
run_ui_locally = True

# Tilt warns is if we try to use tilt against a cluster named 'production'
# Use this line to allow it for now
allow_k8s_contexts('production-llm-service-admin@production-llm-service')

# TODO: Include image builds in tilt up
# docker_build("images/ui-base/")

chart_yaml = helm(
    "chart/",
    values="hu-dev-values.yml",
    # Enable/disable remote UI install depending on if we're running it locally
    set="ui.enabled={}".format(not str(run_ui_locally).lower()),
)
k8s_yaml(chart_yaml)

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
        cmd="".join([
            "([[ -d {} ]] || python3 -m venv {})".format(venv_name, venv_name),
            "&& source {}/bin/activate".format(venv_name),
            "&& pip install -r {}".format(requirements),
        ])
    )

    # Run web app locally
    local_resource(
        name="gradio-app",
        deps=["chart/web-app/"],
        resource_deps=["gradio-app-venv"],
        serve_cmd="".join([
            "cd chart/web-app",
            "&& python app.py",
        ])
    )