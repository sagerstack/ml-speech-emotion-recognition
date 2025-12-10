# Machine Learning Speech Emotion Recognition

## Project Overview
End-to-end speech emotion recognition system with:
- Jupyter notebooks for model development and experimentation
- FastAPI backend (Clean Architecture) serving local and SageMaker-hosted models
- Streamlit frontend for uploads, inference visualization, monitoring, and history
- Deployment stacks for Docker Compose, Kubernetes, and AWS SageMaker

## Jupyter Notebook & Model Training Setup
INSTRUCTIONS TO RETRAIN THE MODELS IN ITS ENTIRETY (TAKES 3-4HRS TO RUN)  
*NOTE:* Due to the number of experiments that you have to run, each notebook will take 3-4 hours to run.

1. git clone https://github.com/sagerstack/ml-speech-emotion-recognition.git  
2. Download CREMA-D Dataset:  
   - Navigate to https://drive.google.com/drive/folders/1tvWeyxZM0bvKVhogRD1yCnwnpgOScJet?usp=share_link  
   - Download `AudioWAV` folder in its entirety, and place the folder in `notebooks/AudioWAV`.  
   - Alternatively, you may download CREMA-D Dataset from: https://www.kaggle.com/datasets/ejlok1/cremad  
   - Ensure you unzip the audio files into `notebooks/AudioWAV` directory.  
3. Install required python packages: `pip install -r requirements.txt`  
4. Open `PART A - Baseline Models.ipynb` or `PART B - Systematic Improvements.ipynb` in Jupyter Notebook.  
5. Run all cells in order (Kernel → Restart & Run All).  
6. Training results and plots will be displayed at the end.

## ML Application Setup For Local Inference & Testing
- Download the v6 model and reference_dataset from [Google Drive](https://drive.google.com/drive/folders/1p75TDFogCS5wt4x7VrA1JJcoVBDXTIfh?usp=drive_link)
- Next, follow the setup and deployment instructions in [user-guide-local-setup.md](docs/user-guides/user-guide-local-setup.md).

## Project Structure
```
ml-speech-emotion-recognition/
├── backend/          # FastAPI service, monitoring, models, tests
├── frontend/         # Streamlit UI for inference, metrics, monitoring
├── deployment/       # Docker, Kubernetes, monitoring, infrastructure assets
├── notebooks/        # Jupyter notebooks for training/experiments
├── data/             # Local datasets (gitignored)
├── scripts/          # Utility scripts (upload, deploy, Terraform helpers)
├── docs/             # Architecture, operations, user guides
├── specs/            # Feature specs and user stories
├── reports/          # Project artifacts
└── README.md         # Local stack composition
```



### How to Access the App and Important URLs
- Streamlit UI: http://localhost:8501 (or the port you configured in the guide)  
- API docs: http://localhost:8000/docs  
- Health check: http://localhost:8000/health  
- If running via Minikube, use the service URLs listed in the local setup guide.

### Running Inference
- In the Streamlit UI, click **Emotion Inference**.  
- **Step 1 – Audio input:** Upload an audio file or record live audio, then click **Analyze Audio**.  
  ![Step 1 – Audio Input](docs/user-guides/01-audio-input.png)  
- **Step 2 – Feature analysis:** Inspect waveform, mel spectrogram, MFCCs, and prosodic features generated locally.  
  ![Step 2 – Feature Analysis](docs/user-guides/02-feature-analysis.png)  
- **Step 3 – Predict emotion:** Review predicted emotion and probability chart; submit feedback with the actual emotion to improve drift monitoring (available when the backend is online).  
  ![Step 3 – Predict Emotion](docs/user-guides/03-predict-emotion.png)  
- Repeat with multiple samples to populate monitoring buffers and history.

### Drift Monitoring
- Open **Drift Monitoring** in the Streamlit sidebar to view the Evidently summary, buffered counts, and latest HTML report.  
- Current local workflow: log ~10 predictions (ideally with feedback) to fill the buffer, then trigger a fresh report:  
  ```bash
  curl -X POST http://localhost:8000/v1/monitoring/generate
  ```  
- After generation, **Drift Monitoring** page will automatically pull the latest summary and any reports already generated 
 
- Note: In production this step is automated when the buffer crosses configured thresholds (e.g., auto-generate at 100 predictions; buffer max 500).

### Observability

- Launch the two pre-configured Grafana dashboards from the UI using the following links: **App Metrics** (application metrics) and **EKS Cluster** (cluster/runtime health).  
- Prometheus expression browser (raw metrics): http://localhost:9090 (when monitoring stack is running).

## Additional Documentation
- Detailed architecture, workflows, and user stories live in `docs/` and `specs/`.
- CI/CD pipelines are defined in `.github/workflows/`.
