import sys
import time

from gradio_client import Client

gradio_host = sys.argv[1]

retries = 60
for n in range(1, retries+1):
    try:
        client = Client(gradio_host)
        result = client.predict(
    		image_url="https://miro.medium.com/v2/resize:fit:1100/format:webp/1*xDgN0L2RfkS8Kc7uTwsRqw.jpeg",
    		prompt="Hi",
    		api_name="/predict"
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
