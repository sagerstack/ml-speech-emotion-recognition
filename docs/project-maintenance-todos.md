# Project Cleanup & Maintenance for Submission

## Expectations
[ ] The repository is well-structured and well-documented.
[ ] Usage and installation instructions are clear.
[ ] Code is well-organized and documented.
[ ] Code is reproducible, extensible, and modular.
[ ] Create an end-to-end ML pipleline and include a pipeline diagram in the report.
[ ] Your report should contain everything we need to know to run your code (including 
the package dependencies)

## Code Submission
Your recapitulative report shall be submitted in a PDF format, along with your code. 

[ ] A Jupyter Notebook, combining MarkDown cells and code cells, 
[ ] Along with .py files containing the largest parts of your code (you just have to 
import them later in your Jupyter Notebook, to minimize the amount of code in 
your Notebook!) But ultimately, the choice is yours!

Environment & reproducibility
[ ] Provide requirements.txt/environment.yml (or pyproject.toml) and optional 
Dockerfile.
[ ]  Document exact commands to reproduce the pipeline and figures; include 
seeds and hardware notes
[ ] Lightweight demo (FastAPI/Flask or batch script) showing how the artifact 
would be consumed. Mention monitoring needs (latency, drift) if deployed.


We strongly advise to upload your submission (code/notebooks + PDFs, but no dataset due to 
space restrictions) on a Github repository. You can then submit the link to your public Github 
repository, during your submission on edimension. 
• Your Github repository for this project should contain your PDF report, your 
DOCUMENTED code/notebook files. It should also contain directions showing the 
required libraries and steps needed to re-train the model from scratch. And more 
importantly, it should also contain clear directions on how to recreate the exact trained 
model and its performance results you are presenting in the PDF. This is essential, for 
reproducibility reasons


