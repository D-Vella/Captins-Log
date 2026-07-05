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