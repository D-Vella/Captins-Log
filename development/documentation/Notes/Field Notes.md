# To - Do:
* Create a new environment for the application!
* Clean up the file structure!

Ran the benchmark between gaming pc and mini pc for LLM work. 
* Gaming PC = 12 seconds
* Mini Pc = 33 Seconds

Performance is acceptable.

Ran into an issue with the requirements.txt file. It turns out I have been using the same environment across 6 different projects! 

Claude instroduced me to the function `pipreqs` which actively scans my .py files.

NOTE: When using `docker build -t captinslog .` that period at the end is IMPORTANT!

Hit compose errors and used the recommended AI assistant in Docker Desktop and got this nugget of info!

> The Windows path C:\Users\dsvel\.ollama\models is replaced with ~/.ollama/models, which expands to your home directory and works cross-platform. If you're running on Windows with WSL2, Docker Desktop will handle the path translation automatically. If you need a different mount location, adjust the left side of the volume as needed.

Docker building is now being handled by the Git Hub Actions CICD process. Provided I keep my repo public it is seemingly free.
Deployment to the mini pc is still manual.

The `requirements.txt` needs to contain both `alembic==1.18.5` & `psycopg2-binary==2.9.12` which the `pipreqs` misses.