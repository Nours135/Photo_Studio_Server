# AI Photo Studio

AI Photo Studio is a scalable, production-ready image processing service powered by deep learning models. It provides a complete end-to-end solution featuring user authentication, asynchronous task processing, real-time progress monitoring, and cloud-ready storage integration. Currently supports AI-powered background removal using U2Net, with an extensible architecture designed to accommodate multiple AI models and processing types.

## Demo

Demo link: [http://18.191.20.249/](http://18.191.20.249/)

## Architecture Overview

```
                                   ┌─────────────────┐
                                   │   PostgreSQL    │
                                   │    Database     │
                                   └────────▲────────┘
                                            │ R/W
                                   ┌────────┴────────┐
                                   │                 │
                         ┌─────────┴────────┐        │
                         │                  │        │
┌─────────────┐          │  FastAPI Web     │        │
│   Client    │◀────────▶│    Service       │        │
│  (Browser)  │   HTTP   │                  │        │
└──────▲──────┘          └─┬────────┬───────┘        │
       │                   │        │                │
       │ SSE               │        │                │
       │(via Web)          │Enqueue │Subscribe       │
       │                   │        │                │
       └───────────────────┼────────┼────────────────┘
                           │        │
                           ▼        ▼
                    ┌─────────────┐          ┌─────────────┐
                    │    Redis    │          │   Storage   │
                    │   Queue +   │          │  (AWS S3)   │
                    │   Pub/Sub   │          └──────▲──────┘
                    └──────▲──────┘                 │
                           │                        │ R/W
                           │Dequeue                 │
                           │& Publish               │
                    ┌──────┴────────────────────────┴──┐
                    │         Worker Process           │
                    │  ┌────────────────────────────┐  │
                    │  │   Model Orchestrator       │  │
                    │  │  ┌───────────────────────┐ │  │
                    │  │  │ AI Models (U2Net...)  │ │  │
                    │  │  └───────────────────────┘ │  │
                    │  └────────────────────────────┘  │
                    └──────────────┬───────────────────┘
                                   │ Update Status
                                   ▼
                              PostgreSQL
```

## Key Features / Highlights

### Distributed Architecture
- **Task Orchestration Framework**: Model orchestrator pattern that manages lifecycle of multiple AI models and task types concurrently
- **Asynchronous Task Queue System**: Redis-based task queue with configurable worker concurrency, enabling horizontal scaling of processing workers
- **Event-Driven Real-Time Updates**: Server-Sent Events (SSE) with Redis Pub/Sub for live task progress streaming to clients
- **Multi-Storage Backend Support**: Abstract storage layer supporting both local filesystem and AWS S3, easily extensible to other cloud providers

### Reliability & Performance
- **Automatic Retry Mechanism**: Failed tasks are automatically re-queued with configurable retry policies
- **Rate Limiting & Security**: Multi-tier API rate limiting (strict/moderate/lenient) to prevent abuse and ensure service stability


### Production-Ready Features
- **User Authentication System**: Complete user registration, login, and session management with Argon2 password hashing
- **Task Lifecycle Management**: Full task state tracking (PENDING → PROCESSING → COMPLETED/FAILED) with database persistence
- **File Validation & Security**: File type and size validation, secure file handling with UUID-based naming
- **Responsive Web Interface**: Modern HTML/CSS/JavaScript frontend for file uploads and task monitoring

## Technical Stack

**Backend**: FastAPI, SQLAlchemy, PostgreSQL, Redis  
**AI/ML**: U2Net (Background Removal), PyTorch  
**Storage**: AWS S3 (aioboto3)  
**Deployment**: Docker Compose  
**Security**: Argon2, JWT/Session-based authentication, API rate limiting

## How to Run

Set up environment variable and aws. 

Start Service by:
```{bash}
uvicorn app.main:app --host 0.0.0.0 --port YOUR_PORT
```
and start one worker by:
```{bash}
python -m worker.main
```


## NEXT (Further Development Plan)

### Model & Features
- [ ] Add more AI models:
  - Style transfer
  - Object detection and segmentation
  - Face detection and beautification
- [ ] AWS Lambda integration for serverless worker execution 
- [ ] Add support for custom model parameters per request
- [ ] Add webhook support for task completion notifications

### Developer & Operations
- [ ] Create admin dashboard for system monitoring
- [ ] Implement usage analytics and billing system

### Infrastructure & Scalability
- [ ] Add Prometheus metrics and Grafana dashboards for monitoring
- [ ] Amazon SQS as alternative queue backend for better cloud integration
- [ ] Kubernetes deployment configuration

---

**Tech Stack**: Python • FastAPI • PostgreSQL • Redis • Docker • PyTorch • AWS S3

**License**: MIT
