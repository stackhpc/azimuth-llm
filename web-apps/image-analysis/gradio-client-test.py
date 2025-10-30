import sys
import time

from gradio_client import Client

gradio_host = sys.argv[1]

retries = 60
for n in range(1, retries + 1):
    try:
        client = Client(gradio_host)
        result = client.predict(
            image_url="https://media.licdn.com/dms/image/v2/D4D0BAQHyxNra6_PoUQ/company-logo_200_200/company-logo_200_200/0/1704365018113/stackhpc_ltd_logo?e=1747872000&v=beta&t=Ed3-KZS-sHlg-ne1KC0YjI4Ez7yVvJzWr103nm5eVK0",
            prompt="Hi",
            api_name="/predict",
        )
        print(result)
        break
    except Exception as err:
        msg = f"Attempt {n} / {retries} encounter error: {err}"
        if n < retries:
            print(msg, "- waiting 10 seconds before retrying")
            time.sleep(10)
        else:
            print(msg, "- no more retries left")
