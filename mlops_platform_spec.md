# Distributed ML Experiment Platform (ModelForge)

## Project Goal

Build a cloud-native MLOps platform that allows users to:

1. Create accounts
2. Upload datasets (CSV / Parquet)
3. Launch ML training jobs
4. Monitor training progress
5. Store and version trained models
6. Deploy models as prediction endpoints
7. Track experiments
8. View metrics through a web dashboard

The platform should demonstrate:

- Backend / Platform Engineering (API design, distributed job processing, reliability)
- DevOps / Infrastructure (IaC, Kubernetes, CI/CD, observability)
- Distributed Systems (queueing, retries, idempotency, horizontal scaling)
- MLOps (experiment tracking, model registry, serving)

This project is intended as a portfolio project primarily for **Backend / Platform Engineering** and **DevOps / SRE** positions.

### Guiding Principles

- **Reproducibility is the headline feature.** The entire platform must come up with a single `docker-compose up`, and the cloud infrastructure must be fully defined as code (Terraform). No click-ops.
- **Nearly-free to run.** Daily development runs entirely locally (Docker Compose, `kind`, LocalStack). Real AWS is used only briefly to prove the Terraform works, then torn down.
- **Build vertically, ship early.** Every phase below leaves a working, demoable system. Finish a thin end-to-end slice before adding breadth.
- **Use industry tools, don't reinvent them.** Integrate MLflow rather than hand-rolling experiment tracking.

---

# Technology Stack

## Frontend

- React
- TypeScript
- Vite
- Material UI

Purpose:
- Dashboard
- Authentication
- Dataset management
- Experiment monitoring
- Model deployment management

> Note: Frontend is intentionally kept **functional but plain** — this is not a frontend-focused project. A clean, working dashboard is sufficient; do not sink weeks into UI polish.

## Backend API

- FastAPI

Purpose:
- REST API
- Authentication
- Dataset management
- Job submission
- Experiment tracking
- Model registry

Requirements:
- Pydantic validation
- OpenAPI documentation
- JWT authentication
- Role-based authorization

## Database

- PostgreSQL
- SQLAlchemy ORM
- Alembic migrations

Store:
- Users
- Datasets
- Experiments
- Training Jobs
- Models
- Deployments

## Object Storage

- AWS S3 (in production)
- **LocalStack** as a drop-in S3 replacement for local development (no real AWS needed)

Store:
- Uploaded datasets
- Trained models
- Training artifacts
- Logs

Structure:

```text
s3://datasets/
s3://models/
s3://artifacts/
```

## Background Processing

- Redis (broker + result backend)
- Celery (workers)

Handle:
- Training jobs
- Model evaluation
- Artifact generation

Reliability requirements (see Phase 3):
- Automatic retries with exponential backoff
- Idempotent job processing
- Graceful handling of a worker dying mid-training
- Dead-letter queue for permanently failed jobs

## Experiment Tracking & Model Registry

- **MLflow** (self-hosted, runs locally in Docker)

Used for:
- Logging parameters, metrics, and artifacts per run
- Model registry with versioning and stage transitions

> We integrate MLflow rather than reimplementing it — using industry-standard tooling is a stronger signal than rebuilding it.

## Containerization

- Docker

Containers:
- frontend
- backend
- postgres
- redis
- worker
- mlflow
- localstack (dev only)
- prometheus
- grafana

Provide:
- A `Dockerfile` per service (multi-stage builds)
- `docker-compose.yml` for one-command local startup

## Orchestration

- **Kubernetes** (local via `kind` or `k3d` — 100% free, runs on the dev machine)
- Plain manifests and/or a Helm chart

Demonstrates:
- Workers as a scalable `Deployment` (`kubectl scale --replicas=N`)
- Horizontal scaling story for the distributed job system
- Liveness / readiness probes
- ConfigMaps and Secrets

## Infrastructure as Code

- **Terraform** (lives in `infrastructure/`)

Defines AWS resources:
- EC2 / RDS / S3 / networking / IAM

Workflow:
- `terraform plan` runs on every PR (in CI)
- `terraform apply` run briefly against AWS free tier to prove it works (capture screenshots)
- `terraform destroy` immediately after to stop all billing

> The infrastructure *code* stays in the repo permanently as proof, even though no AWS resources run 24/7.

## CI/CD

- GitHub Actions

Pipeline:
1. Run tests (pytest)
2. Run linting + formatting (ruff / black) and type-checking (mypy)
3. Build Docker images (multi-stage)
4. Push images to **GHCR** (GitHub Container Registry — free)
5. Scan images for vulnerabilities (**Trivy** — free)
6. Spin up a `kind` cluster inside the Action and run integration tests against real Kubernetes
7. Run `terraform plan` on PRs to surface infra changes

## Observability

- Prometheus (metrics scraping)
- Grafana (dashboards)

Track:
- API latency (capture p50 / p95 / p99 — put concrete numbers in the README)
- Training duration
- Job throughput and queue depth
- Failed jobs
- CPU / memory usage

## Cloud Infrastructure (production target, used briefly)

AWS Services (all defined in Terraform):
- EC2
- RDS (PostgreSQL)
- S3

---

# Build Order

Each step leaves a **working, demoable system**. Do them in order; do not move on until the current slice runs end-to-end.

1. **Vertical slice (hardest milestone — do first).** FastAPI + Postgres + one Celery worker + LocalStack S3. Upload a CSV → train a sklearn model → store metrics → GET them back. No auth, no frontend yet.
2. **Authentication** (JWT / bcrypt).
3. **Job-system reliability** (retries + backoff, idempotency, dead-letter queue, worker-failure handling).
4. **Experiment tracking** via MLflow integration.
5. **Model registry & serving** (versioning, deploy as prediction endpoints).
6. **React dashboard** (functional, plain).
7. **Dockerize everything** — `docker-compose up` brings the whole stack live.
8. **CI/CD** in GitHub Actions (tests, lint, build, push to GHCR, Trivy scan, kind integration tests).
9. **Kubernetes** — `kind` manifests / Helm chart + a worker scaling demo.
10. **Terraform** AWS infra — apply briefly, screenshot, destroy.
11. **Prometheus + Grafana** observability — capture latency/throughput numbers.
12. **README polish** — architecture diagram, one-command startup, demo GIF, captured metrics.

---

# Phase 1: Authentication

Features:
- Register
- Login
- Logout
- JWT Tokens
- Password Hashing

Requirements:
- bcrypt
- Access tokens expire after 1 hour
- Refresh token support
- Role-based authorization (e.g. `user`, `admin`)

---

# Phase 2: Dataset Management

## Upload Dataset

Endpoint:

```http
POST /datasets
```

Accept:
- CSV
- Parquet

Store files in S3 (LocalStack locally) and metadata in PostgreSQL.

Metadata:
- dataset_id
- owner
- filename
- size
- row_count / column_count
- upload_time

## Dataset Listing

```http
GET /datasets
```

Show:
- Name
- Size
- Creation date

---

# Phase 3: Training Job System

## Create Training Job

```http
POST /jobs
```

Example:

```json
{
  "dataset_id": 1,
  "model_type": "random_forest",
  "target_column": "price"
}
```

Push job into the Redis queue (Celery).

ML scope is intentionally **boring and CPU-only**: scikit-learn tabular models
(random forest, logistic regression, gradient boosting). No deep learning, no GPU.

Worker responsibilities:
1. Download dataset (idempotently)
2. **Detect task type** (classification vs. regression) from the target column
3. Train model
4. Evaluate model with **task-appropriate metrics** (see Phase 4)
5. Log the run to MLflow (params, metrics, artifacts)
6. Save model artifact to S3
7. Update status

Statuses:
- Queued
- Running
- Completed
- Failed

## Reliability (the distributed-systems story)

This is a core differentiator — implement real failure handling, not just the happy path:

- **Retries with exponential backoff** on transient failures
- **Idempotent processing** — re-running a job must not corrupt state or duplicate artifacts
- **Worker-failure recovery** — if a worker dies mid-training, the job is re-queued (visibility timeout / acks-late)
- **Dead-letter queue** — permanently failed jobs land somewhere inspectable instead of vanishing

---

# Phase 4: Experiment Tracking (MLflow)

Integrate **MLflow** (self-hosted in Docker) rather than reimplementing tracking.

Log per run:
- experiment_id / run_id
- parameters
- metrics
- training_time
- artifact_path

**Task-aware metrics** (auto-selected by detected task type):

- Classification: accuracy, precision, recall, f1
- Regression: RMSE, MAE, R²

Users can compare experiments side-by-side in the dashboard and in the MLflow UI.

---

# Phase 5: Model Registry (MLflow)

Use the **MLflow Model Registry**.

Track:
- model name / version
- source run (experiment_id / run_id)
- stage

Stages:
- Staging
- Production
- Archived

Support model versioning (v1, v2, v3) with rollback capability.

---

# Phase 6: Model Serving

Deploy models as prediction endpoints.

```http
POST /deployments
```

Creates:

```http
/predict/{deployment_id}
```

Example response:

```json
{
  "prediction": 0.82
}
```

Inference runs inside **sandboxed Docker containers** with resource limits
(CPU / memory caps), since the served models are user-influenced. Be ready to
discuss the isolation and resource-limit story in interviews.

---

# Phase 7: Monitoring Dashboard

Pages:
- Dashboard
- Datasets
- Experiments
- Models
- Deployments

Display:
- Active jobs
- Completed jobs
- Failed jobs
- Model performance

Keep the UI functional and plain.

---

# Phase 8: CI/CD

GitHub Actions pipeline:

1. Run tests (pytest)
2. Lint + format check (ruff / black) + type-check (mypy)
3. Build multi-stage Docker images
4. Push images to GHCR
5. Scan images with Trivy
6. Spin up a `kind` cluster in the Action and run integration tests against real k8s
7. Run `terraform plan` on PRs

---

# Phase 9: Kubernetes (local, free)

Provide Kubernetes manifests and/or a Helm chart, runnable on `kind` / `k3d`.

Demonstrate:
- Workers as a scalable `Deployment` (`kubectl scale --replicas=N`)
- Liveness / readiness probes
- ConfigMaps + Secrets for configuration
- The horizontal-scaling story for the job queue

`docker-compose.yml` remains as the simple local path; k8s is the "production-shaped" path.

---

# Phase 10: Infrastructure as Code (Terraform)

Infrastructure (all in `infrastructure/`, written in Terraform):

- EC2 (backend / worker)
- RDS PostgreSQL
- S3
- Networking + IAM

Requirements:
- Environment variables
- Secret management
- HTTPS
- Nginx reverse proxy

Workflow:
- `terraform plan` on PRs (CI)
- `terraform apply` against AWS free tier briefly → screenshot → `terraform destroy`

The Terraform code is permanent proof of IaC skill, even with nothing running 24/7.

---

# Phase 11: Observability

Tools:
- Prometheus
- Grafana

Track:
- API latency (capture p50 / p95 / p99)
- Training duration
- Job throughput / queue depth
- Failed jobs
- CPU usage
- Memory usage

Capture concrete numbers (e.g. "p95 inference latency ~40ms, sustained N req/s")
and put them in the README — concrete metrics beat feature lists on a resume.

---

# Deferred / Optional (low resume value — do last or skip)

- Email notifications when jobs complete
- Scheduled retraining (Celery Beat: daily / weekly / monthly)

These are fiddly and add little signal for Backend/DevOps roles. Defer until
everything above is solid.

---

# Repository Structure

```text
root/
├── frontend/
├── backend/
├── worker/
├── infrastructure/      # Terraform
├── k8s/                 # Kubernetes manifests / Helm chart
├── docker/
├── .github/workflows/   # CI/CD
└── docs/
```

---

# Learning Goals

- Docker (multi-stage builds)
- Kubernetes (kind / k3d, Helm)
- Terraform (IaC)
- AWS (EC2, RDS, S3)
- LocalStack
- PostgreSQL + Alembic
- Redis + Celery (retries, idempotency, dead-letter queues)
- FastAPI
- MLflow
- React
- GitHub Actions (GHCR, Trivy, kind-in-CI)
- Prometheus + Grafana
- Distributed Systems
- MLOps

---

# Success Criteria

A user can:

1. Register
2. Upload a dataset
3. Train a model (classification or regression, with correct metrics)
4. View experiment metrics
5. Register and version a model
6. Deploy a model
7. Send prediction requests
8. Monitor deployments through the dashboard

And, as a platform/infra proof:

- The entire stack comes up with a single `docker-compose up`
- The same stack runs on Kubernetes via `kind`
- All cloud infrastructure is defined in Terraform and reproducible from scratch
- CI/CD builds, scans, tests (against real k8s), and validates infra on every PR
- Observability dashboards expose real latency and throughput numbers
