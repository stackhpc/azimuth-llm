#!/bin/bash
#SBATCH --job-name=my_job_name        # Job name
#SBATCH --output=output.txt           # Standard output file
#SBATCH --error=error.txt             # Standard error file
#SBATCH --nodes=10                    # Number of nodes
#SBATCH --ntasks-per-node=1           # Number of tasks per node
#SBATCH --cpus-per-task=1             # Number of CPU cores per task
#SBATCH --time=1:00:00                # Maximum runtime (D-HH:MM:SS)

#Your job commands go here
cat << EOF > run.py

from gradio_client import Client

client = Client("https://insert-public-llm-address/")


for i in range(10):
    result = client.predict("Tell me a short story", api_name="/chat")
    print(result)

EOF

if [[ ! -d gradio-env ]]; then
  python3 -m venv gradio-env
fi

source gradio-env/bin/activate
pip list | grep gradio || pip install gradio

srun python3 run.py
