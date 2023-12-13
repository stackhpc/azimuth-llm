import requests, time


def wait_for_backend(url):
    """
    This function acts as a startup check so that the frontend web app does not
    accept requests until the backend API is up and running.
    """
    ready = False
    while not ready:
        try:
            ready = requests.get(f"{url}/health").status_code == 200
            print("Waiting for backend API to start")
            time.sleep(1)
        except requests.exceptions.ConnectionError as e:
            pass
    return
