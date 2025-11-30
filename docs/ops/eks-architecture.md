# AWS EKS Deployment Diagram

```mermaid
graph LR
    subgraph Clients
        A[Browser / Streamlit User]
        B[API Consumer / External Client]
    end

    subgraph Networking
        LBALB[AWS NLB/ALB<br/>Public Ingress]
    end

    subgraph "EKS Control Plane"
        CP[AWS Managed Control Plane<br/>API Server + etcd]
    end

    subgraph "EKS Worker Nodes (us-east-1 private subnets)"
        subgraph NodeGroup1["Node Group - On-Demand"]
            POD1[Streamlit Deployment<br/>2 Pods<br/>Container Port 8501]
            POD2[FastAPI Deployment<br/>3 Pods<br/>Container Port 8000]
        end
    end

    subgraph "AWS Services"
        S3[(S3 Bucket<br/>temp audio storage)]
        SM[(SageMaker Endpoint)]
        CW[(CloudWatch / Prometheus Metrics)]
    end

    %% External to ingress
    A -- "HTTPS 443 / WSS" --> LBALB
    B -- "HTTPS 443" --> LBALB

    %% Ingress to Services
    LBALB -- "HTTP 8501" --> POD1
    LBALB -- "HTTP 8000" --> POD2

    %% Internal pod communication
    POD1 -- "REST API<br/>HTTP 8000" --> POD2

    %% Pods to AWS services
    POD2 -- "S3 SDK<br/>HTTPS 443" --> S3
    POD2 -- "InvokeEndpoint<br/>HTTPS 443" --> SM
    POD2 -- "Metrics<br/>HTTP 9090" --> CW

    %% Control plane relationships
    CP -.-> POD1
    CP -.-> POD2
```

### Diagram Notes

- **Ingress / Load Balancer**: An AWS Application or Network Load Balancer terminates TLS and routes traffic to the appropriate service inside the EKS cluster.
- **Streamlit Pods**: Serve the ML UI on port 8501. They reach the backend using the cluster service (`http://backend:8000`).
- **FastAPI Backend Pods**: Provide `/v1/infer/infer` and supporting APIs on port 8000. They connect to AWS resources (S3 for temporary audio storage, SageMaker for inference, CloudWatch/Prometheus for metrics) over HTTPS.
- **Control Plane**: Managed by AWS; communicates with worker nodes to schedule pods and manage cluster state.
- **Metrics**: Pods expose `/metrics` on port 9090 for Prometheus scraping; CloudWatch handles infrastructure logs/metrics.
