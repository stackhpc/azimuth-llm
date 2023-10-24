import requests, time

def wait_for_backend(url):
    ready = False
    while not ready:
        try:
            ready = (requests.get(f'{url}/health').status_code == 200)
            print('Waiting for backend API to start')
            time.sleep(5)
        except requests.exceptions.ConnectionError as e:
            pass
    return