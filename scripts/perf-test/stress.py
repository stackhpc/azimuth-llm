# NOTE: In its current state this script is not a useful benchmark for the LLM system.
# It seems that Gradio is doing some kind of session based queuing which results in serial
# execution of requests even when multiple Gradio client instances running inside separate
# python jobs are created via Joblib. This script should be updated in the future once the
# Gradio session behaviour is better understood, but for now the perf-test jupyter notebook
# should be used to benchmark an LLM running on the same Kubernetes cluster by directly
# targetting the internal service corresponding to the backend API.

import time, random
import pandas as pd
from gradio_client import Client
from joblib import Parallel, delayed

url = "http://localhost:7860"

prompts = [
    "Hi, how are you?",
    "What's the weather like with you?",
    "Who's the best footballer of all time?"
]

client_count = 3
request_count = 5 # Requests per client

def make_requests(client_id: int):
    client = Client(url)
    timings = []
    for n in range(request_count):
        print(f"Starting request {n+1}/{request_count} for client {client_id}")
        start_time = time.time()
        client.predict(random.choice(prompts), api_name="/chat")
        timings.append(time.time() - start_time)
    return timings

results = list(Parallel(n_jobs=client_count)(delayed(make_requests)(i) for i in range(1, client_count+1)))
all_timings = []
for client_timings in results:
    all_timings += client_timings
print(pd.Series(all_timings).describe())
