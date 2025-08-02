# Coffee - Men-Only Friend Rating Backend

A production-ready REST API backend for rating and reviewing friends, featuring AWS integration, face recognition, and comprehensive security measures.

## Features

- **Men-only registration** with AWS Rekognition face verification
- **Friend photo upload** and verification with liveness detection
- **Dual photo verification** ensuring user and friend appear together
- **Rating and comment system** with AWS Comprehend text moderation
- **Secure AWS integration** (Rekognition, S3, DynamoDB, Comprehend)
- **JWT authentication** with bcrypt password hashing
- **Production-ready deployment** with SAM and CloudFormation
- **Comprehensive testing** and CI/CD pipeline

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Mobile App    │────│   API Gateway    │────│   Lambda        │
│                 │    │   (REST API)     │    │   (Flask App)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       │                                 │                                 │
                ┌──────▼──────┐    ┌──────────────┐    ┌▼──────────────┐    ┌─────────────▼────┐
                │ DynamoDB    │    │ S3 Uploads   │    │ Rekognition   │    │ Comprehend       │
                │ (Users,     │    │ (Images)     │    │ (Face AI)     │    │ (Text Moderation)│
                │ Friends,    │    │              │    │               │    │                  │
                │ Ratings)    │    │              │    │               │    │                  │
                └─────────────┘    └──────────────┘    └───────────────┘    └──────────────────┘
```

## Quick Start

### Prerequisites

- **Python 3.12+**
- **AWS CLI** configured with appropriate permissions
- **SAM CLI** installed ([Installation Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html))

### 1. Clone Repository

```bash
git clone <repository-url>
cd coffee
```

### 2. Deploy to AWS (Recommended)

```bash
# Deploy to development environment
./deploy.sh dev "your-super-secret-jwt-key-here"

# Deploy to production environment  
./deploy.sh prod "different-production-jwt-key"
```

The deployment script will:
- ✅ Build and deploy all AWS resources
- ✅ Configure environment variables automatically
- ✅ Test the deployment
- ✅ Provide you with the API URL
- ✅ Create local `.env.dev` file for testing

### 3. Local Development (Optional)

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure local environment
cp .env.example .env
# Edit .env with your AWS credentials

# Option A: Local Flask development
python src/app.py

# Option B: SAM local (mimics AWS Lambda)
sam local start-api --port 3000
```

## API Documentation

### Complete API Specification
- **OpenAPI 3.1**: See `openapi.yaml` for complete specification
- **Test Collection**: Use `launch.http` with VS Code REST Client

### Key Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | ❌ | Register user (men-only verification) |
| `POST` | `/auth/login` | ❌ | Login user |
| `POST` | `/uploads/presign` | ✅ | Get S3 presigned upload URL |
| `POST` | `/friends/verify` | ✅ | Verify friend photos with face recognition |
| `POST` | `/friends/{id}/rate` | ✅ | Rate friend with text moderation |
| `GET` | `/friends/search` | ❌ | Search friends with pagination |
| `GET` | `/friends/{id}` | ❌ | Get friend profile and ratings |
| `GET` | `/friends/{id}/photos` | ❌ | Get friend photos (paginated) |
| `GET` | `/me` | ✅ | Get current user profile |
| `GET` | `/health` | ❌ | Health check |

### Face Verification Flow

1. **Registration**: User uploads selfie → Rekognition verifies gender = Male
2. **Friend Upload**: User gets presigned URLs → Uploads friend solo + duo photos to S3
3. **Verification**: 
   - Rekognition checks face liveness in both photos
   - Compares faces to ensure friend appears in both photos
   - Verifies user appears in duo photo
   - Checks for duplicate friends in face collection
4. **Storage**: Creates/links friend record in DynamoDB

## Deployment Environments

### Development Environment
```bash
./deploy.sh dev "dev-jwt-secret"
```
- Stack: `coffee-dev`
- URL: `https://{api-id}.execute-api.us-east-1.amazonaws.com/dev`
- Resources: `coffee-table-dev`, `coffee-uploads-dev-{account-id}`

### Production Environment
```bash
./deploy.sh prod "prod-jwt-secret"
```
- Stack: `coffee-prod`
- URL: `https://{api-id}.execute-api.us-east-1.amazonaws.com/prod`
- Resources: `coffee-table-prod`, `coffee-uploads-prod-{account-id}`

## Testing

### Run Tests Locally
```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test files
pytest tests/test_auth.py -v
```

### Manual API Testing
```bash
# Use VS Code REST Client with launch.http
# Or use curl/Postman with the deployed API URL

# Example: Test health endpoint
curl https://your-api-url.amazonaws.com/dev/health

# Example: Register user
curl -X POST https://your-api-url.amazonaws.com/dev/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123","selfieKey":"selfie/test.jpg"}'
```

## Development Workflow

### Code Quality
```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

### CI/CD Pipeline

The GitHub Actions pipeline automatically:
- ✅ Runs tests and linting on every push
- ✅ Deploys to dev environment on push to `develop`
- ✅ Requires manual approval for production deployment
- ✅ Runs security scans
- ✅ Performs integration tests

## Configuration

### Environment Variables

**Local Development (.env):**
```bash
AWS_REGION=us-east-1
AWS_PROFILE=default
DYNAMODB_TABLE_NAME=coffee-table-dev
S3_BUCKET_NAME=coffee-uploads-dev-123456789
REKOGNITION_COLLECTION_ID=coffee-faces
JWT_SECRET_KEY=your-local-secret
```

**Production (AWS Lambda):**
Environment variables are automatically set by CloudFormation from the SAM template.

### AWS Permissions Required

The deployment creates IAM roles with these permissions:
- **DynamoDB**: Full CRUD access to the coffee table
- **S3**: Full access to the uploads bucket
- **Rekognition**: Face detection, comparison, collection management
- **Comprehend**: Text analysis and moderation
- **CloudWatch**: Logging and monitoring
- **X-Ray**: Distributed tracing

## Security Features

- **JWT Authentication** with secure secret rotation
- **Password Hashing** using bcrypt with salt
- **Input Validation** with Pydantic models
- **Text Moderation** using AWS Comprehend
- **Face Liveness Detection** to prevent fake photos
- **S3 Security** with presigned URLs and access controls
- **IAM Least Privilege** with minimal required permissions
- **HTTPS Only** with API Gateway SSL termination

## Mobile Integration

### Typical Mobile App Flow

1. **Registration**:
   ```javascript
   // 1. Get presigned URL for selfie
   const presignResponse = await fetch('/uploads/presign', {
     method: 'POST',
     body: JSON.stringify({kind: 'selfie'})
   });
   
   // 2. Upload selfie to S3
   await fetch(presignResponse.uploadUrl, {
     method: 'POST', 
     body: selfieFile
   });
   
   // 3. Register with selfie key
   const authResponse = await fetch('/auth/register', {
     method: 'POST',
     body: JSON.stringify({
       username: 'user',
       password: 'pass',
       selfieKey: presignResponse.fileKey
     })
   });
   ```

2. **Add Friend**:
   ```javascript
   // Get presigned URLs for friend photos
   const friendUrl = await getPresignedUrl('friend');
   const duoUrl = await getPresignedUrl('duo');
   
   // Upload photos to S3
   await uploadToS3(friendUrl, friendPhoto);
   await uploadToS3(duoUrl, duoPhoto);
   
   // Verify friend
   await fetch('/friends/verify', {
     method: 'POST',
     headers: {Authorization: `Bearer ${token}`},
     body: JSON.stringify({
       friendPhotoKey: friendUrl.fileKey,
       duoPhotoKey: duoUrl.fileKey,
       friendName: 'John',
       friendCity: 'NYC'
     })
   });
   ```

## Monitoring and Logging

- **CloudWatch Logs**: All Lambda logs with structured logging
- **X-Ray Tracing**: Distributed tracing for performance monitoring
- **API Gateway Logs**: Request/response logging with metrics
- **CloudWatch Metrics**: Custom metrics for business logic

## Support

- **Issues**: Report bugs and feature requests in GitHub Issues
- **Documentation**: This README and `openapi.yaml`
- **Testing**: Use `launch.http` for API testing examples

## License

MIT License - see LICENSE file for details.