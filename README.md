# Coffee - Men-Only Friend Rating Backend

A production-ready REST API backend for rating and reviewing friends, featuring AWS integration, face recognition, and comprehensive security measures.

## Features

- Men-only registration with face verification
- Friend photo upload and verification
- Rating and comment system with text moderation
- Secure AWS integration (Rekognition, S3, DynamoDB, Comprehend)
- JWT authentication with bcrypt password hashing
- Comprehensive testing and CI/CD

## Quick Start

### Prerequisites

- Python 3.12+
- AWS CLI configured
- SAM CLI installed

### Local Development Setup

1. Clone and navigate to the repository:
```bash
git clone <repository-url>
cd coffee
```

2. Create and activate virtual environment:
```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your AWS configuration
```

5. Run local development server:
```bash
sam local start-api
```

## API Documentation

The API provides 10 endpoints for user registration, friend management, and rating functionality. See `openapi.yaml` for complete specification.

## Deployment

Deploy to AWS using SAM:
```bash
sam build
sam deploy --guided
```

## Development

- **Linting**: `black src/ && isort src/ && flake8 src/`
- **Type Checking**: `mypy src/`
- **Testing**: `pytest`