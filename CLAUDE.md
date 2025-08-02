# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Coffee is a production-ready REST API backend for a men-only friend rating system. It features AWS integration, face recognition, and comprehensive security measures. The system allows male users to register, upload friend photos, verify relationships through dual photo verification, and rate friends with text moderation.

## Technology Stack

- **Language**: Python 3.12
- **Framework**: Flask 3 with Blueprints and Pydantic models
- **Authentication**: JWT with bcrypt password hashing
- **Cloud**: AWS (API Gateway, Lambda, DynamoDB, S3, Rekognition, Comprehend)
- **Infrastructure**: AWS SAM (Serverless Application Model)
- **Testing**: pytest with moto for AWS service mocking
- **CI/CD**: GitHub Actions with automated testing and deployment

## Repository Structure

```
coffee/
├── src/                          # Main application code
│   ├── app.py                   # Flask application factory + Lambda handler
│   ├── config.py                # Configuration management
│   ├── models/                  # Pydantic models for requests/responses
│   ├── blueprints/              # Flask blueprints for API routes
│   ├── services/                # AWS service integrations
│   └── utils/                   # Authentication and validation utilities
├── tests/                       # Comprehensive test suite
├── template.yaml                # SAM CloudFormation template
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Tool configuration (black, isort, mypy, etc.)
├── deploy.sh                   # Deployment helper script
├── openapi.yaml                # API specification
├── launch.http                 # VS Code REST Client test collection
└── .github/workflows/ci.yml    # CI/CD pipeline
```

## Development Commands

### Local Development
```bash
# Set up environment
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run locally (Flask development)
python src/app.py

# Run locally (SAM - mimics AWS Lambda)
sam local start-api --port 3000
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage
pytest --cov=src tests/
```

### Code Quality
```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Deployment
```bash
# Deploy to development
./deploy.sh dev "your-jwt-secret-key"

# Deploy to production
./deploy.sh prod "your-production-jwt-secret"
```

## Architecture Overview

The application uses a serverless architecture on AWS:

1. **API Gateway** receives HTTP requests and routes to Lambda
2. **Lambda Function** runs the Flask application using AWS Powertools
3. **DynamoDB** stores user, friend, and rating data in a single table
4. **S3** handles image uploads via presigned URLs
5. **Rekognition** performs face detection, liveness checks, and comparisons
6. **Comprehend** moderates text content for inappropriate language

## Key Business Logic

### User Registration (Men-Only)
- User uploads selfie to S3 via presigned URL
- Rekognition DetectFaces API verifies gender = "Male" with 95%+ confidence
- User record created in DynamoDB with hashed password

### Friend Verification Process
- User uploads two photos: friend solo photo + user+friend together photo
- System performs face liveness detection on both photos
- Compares faces to ensure friend appears in both photos
- Verifies user appears in the duo photo
- Checks Rekognition face collection for duplicate friends
- Creates new friend or links to existing friend record

### Rating System
- Users can rate friends 1-10 with comments (max 250 characters)
- Comprehend moderates comments for inappropriate content
- Ratings update friend's aggregate score atomically using DynamoDB UpdateExpressions

## Database Design (DynamoDB Single Table)

```
PK                    SK                    Purpose
USER#{userId}         PROFILE              User account info
FRIEND#{friendId}     METADATA             Friend basic info (name, city, ratings)
FRIEND#{friendId}     PHOTO#{photoKey}     Friend photo records
FRIEND#{friendId}     RATING#{userId}      Individual ratings
```

**Global Secondary Indexes:**
- `username-index`: For user login lookup
- `name_city-index`: For friend search functionality

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | ❌ | Register user (male verification) |
| POST | `/auth/login` | ❌ | Login user |
| POST | `/uploads/presign` | ✅ | Get S3 presigned upload URL |
| POST | `/friends/verify` | ✅ | Verify friend photos |
| POST | `/friends/{id}/rate` | ✅ | Rate friend |
| GET | `/friends/search` | ❌ | Search friends (paginated) |
| GET | `/friends/{id}` | ❌ | Get friend profile |
| GET | `/friends/{id}/photos` | ❌ | Get friend photos (paginated) |
| GET | `/me` | ✅ | Get user profile |
| GET | `/health` | ❌ | Health check |

## Configuration

Environment variables are automatically managed:
- **Local**: `.env` file (copy from `.env.example`)
- **AWS**: CloudFormation sets Lambda environment variables from SAM template

## Testing Strategy

- **Unit Tests**: All services and utilities
- **Integration Tests**: All API endpoints
- **AWS Mocking**: Using moto library for DynamoDB, S3, Rekognition
- **Security Testing**: Bandit for security vulnerabilities
- **Dependency Scanning**: Safety for known vulnerabilities

## Branch Information

- **Current branch**: develop (all development work)
- **Main branch**: master (production releases)
- **CI/CD**: Automatic deployment to dev on `develop` push, manual approval for `master`

## Security Considerations

- JWT tokens with configurable expiry
- Bcrypt password hashing with salt
- Input validation using Pydantic models
- S3 presigned URLs with time limits and size restrictions
- IAM roles with least-privilege permissions
- Text moderation to prevent inappropriate content
- Face liveness detection to prevent fake photos

## Common Tasks

- **Add new API endpoint**: Create route in appropriate blueprint, add Pydantic models, write tests
- **Modify AWS permissions**: Update SAM template IAM policies
- **Change database schema**: Update DynamoDB service methods and related models
- **Add new validation**: Update validation utilities and add corresponding tests
- **Deploy changes**: Use `./deploy.sh` script or GitHub Actions pipeline