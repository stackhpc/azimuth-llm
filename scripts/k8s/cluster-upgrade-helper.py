# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "kubernetes",
# ]
# ///

import time
from typing import List
from kubernetes import client, config

config.load_kube_config()
core = client.CoreV1Api()
apps = client.AppsV1Api()
policy = client.PolicyV1Api()


def find_pdb_deployment(pdb: client.V1PodDisruptionBudget, deployments: client.V1DeploymentList) -> client.V1Deployment:
    pdb_selector = pdb.spec.selector.match_labels
    if not pdb_selector:
        raise Exception(f"PodDisruptionBudget {pdb.metadata.name} has no selector labels to match against")

    matching_deployments = []
    for deployment in deployments.items:
        deployment_selector = deployment.spec.selector.match_labels or {}
        # If the deployment's selector is a subset of the PDB selector, it's a potential match
        if pdb_selector.items() <= deployment_selector.items():
            matching_deployments.append(deployment)
    if len(matching_deployments) != 1:
        raise Exception(f"Found PDB with {len(matching_deployments)} matching deployments")
    return matching_deployments[0]


def deployment_requires_gpu(deployment: client.V1Deployment) -> bool:
    containers = deployment.spec.template.spec.containers
    for c in containers:
        # TODO: USE THIS INSTEAD
        # if c.resources.limits and c.resources.limits.get("nvidia.com/gpu") == 1:
        if c.resources.limits and c.resources.limits.get("nvidia.com/gpu"):
            return True
    return False


def deployment_needs_scale_up(d: client.V1Deployment) -> bool:
    return (d.spec.replicas == 1 and deployment_requires_gpu(d))


def get_deployment_pods(d: client.V1Deployment) -> List[client.V1Pod]:
    selector = d.spec.selector.match_labels
    label_selector = ",".join([f"{k}={v}" for k, v in selector.items()])
    return core.list_namespaced_pod(namespace=d.metadata.namespace, label_selector=label_selector).items


def deployment_has_pod_on_node(d: client.V1Deployment, node_name: str) -> bool:
    pod_node_names = [p.spec.node_name for p in get_deployment_pods(d)]
    return any(n == node_name for n in pod_node_names)


def main() -> None:
    scaled_deployments = []
    while True:
        print("Running checks...")
        nodes = core.list_node()
        deployments = apps.list_deployment_for_all_namespaces()
        pdbs = policy.list_pod_disruption_budget_for_all_namespaces()
        # Check for any deployments with PDBs which have pods running
        # on unschedulable (i.e. draining) nodes
        for node in nodes.items:
            if node.spec.unschedulable:
                for pdb in pdbs.items:
                    d = find_pdb_deployment(pdb, deployments)
                    if deployment_has_pod_on_node(d, node.metadata.name) and deployment_needs_scale_up(d):
                        print(
                            f"Found deployment {d.metadata.name} on node {node.metadata.name}"
                            " which requires manual scale up to activate pdb"
                        )
                        deployment = apps.patch_namespaced_deployment(
                            d.metadata.name,
                            d.metadata.namespace,
                            {
                                "spec": {
                                    "replicas": 2
                                }
                            }
                        )
                        scaled_deployments.append(deployment)

        for i, d in enumerate(scaled_deployments):
            latest = apps.read_namespaced_deployment(d.metadata.name, d.metadata.namespace)
            has_pod_on_unschedulable_node = any(
                deployment_has_pod_on_node(
                    latest,
                    n.metadata.name
                ) for n in nodes.items if n.spec.unschedulable
            )
            if latest.status.replicas > 1 and not has_pod_on_unschedulable_node:
                # Pause for longer to try to allow next node to be cordoned
                time.sleep(30)
                print(f"Scaling down deployment {d.metadata.name}")
                apps.patch_namespaced_deployment(
                    d.metadata.name,
                    d.metadata.namespace,
                    {
                        "spec": {
                            "replicas": 1
                        }
                    }
                )
                scaled_deployments.pop(i)
        pause = 10
        print(f"Pausing for {pause} seconds")
        time.sleep(pause)

if __name__ == "__main__":
    main()
