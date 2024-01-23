import requests, time
from urllib.parse import urljoin


def wait_for_backend(endpoint):
    """
    This function acts as a startup check so that the frontend web app does not
    accept requests until the backend API is up and running.
    """
    ready = False
    while not ready:
        try:
            ready = requests.get(endpoint).status_code == 200
            print(f"Waiting for 200 status from backend API at {endpoint}")
            time.sleep(1)
        except requests.exceptions.ConnectionError as e:
            pass
    return
