#!/bin/bash

# Coffee Backend Deployment Script
# Usage: ./deploy.sh [dev|prod] [jwt-secret-key]

set -e

STAGE=${1:-dev}
JWT_SECRET=${2}

if [ -z "$JWT_SECRET" ]; then
    echo "Error: JWT secret key is required"
    echo "Usage: $0 [dev|prod] [jwt-secret-key]"
    exit 1
fi

if [ "$STAGE" != "dev" ] && [ "$STAGE" != "prod" ]; then
    echo "Error: Stage must be 'dev' or 'prod'"
    exit 1
fi

echo "🚀 Deploying Coffee Backend to $STAGE environment..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: AWS CLI not configured. Run 'aws configure' first."
    exit 1
fi

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "Error: SAM CLI not installed. Install it first."
    echo "https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
    exit 1
fi

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo "📋 Deployment Details:"
echo "  Stage: $STAGE"
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  AWS Region: $AWS_REGION"
echo "  Stack Name: coffee-$STAGE"

# Build the application
echo "🏗️ Building application..."
sam build --use-container

# Deploy the application
echo "🚀 Deploying to AWS..."
sam deploy \
    --stack-name "coffee-$STAGE" \
    --capabilities CAPABILITY_IAM \
    --region "$AWS_REGION" \
    --parameter-overrides \
        Stage="$STAGE" \
        JWTSecretKey="$JWT_SECRET" \
    --confirm-changeset

# Get the API endpoint
echo "📡 Getting API endpoint..."
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "coffee-$STAGE" \
    --query 'Stacks[0].Outputs[?OutputKey==`CoffeeApiUrl`].OutputValue' \
    --output text \
    --region "$AWS_REGION")

# Test the health endpoint
echo "🏥 Testing health endpoint..."
if curl -s -f "$API_URL/health" > /dev/null; then
    echo "✅ Health check passed!"
else
    echo "❌ Health check failed!"
    exit 1
fi

echo "🎉 Deployment completed successfully!"
echo "🌐 API URL: $API_URL"
echo ""
echo "Next steps:"
echo "1. Update your .env file with the new API URL"
echo "2. Test the API endpoints using the launch.http file"
echo "3. Monitor logs in CloudWatch"

# Create .env file for local testing
cat > ".env.${STAGE}" << EOF
# Coffee Backend Configuration - $STAGE Environment
AWS_REGION=$AWS_REGION
DYNAMODB_TABLE_NAME=coffee-table-$STAGE
S3_BUCKET_NAME=coffee-uploads-$STAGE-$AWS_ACCOUNT_ID
REKOGNITION_COLLECTION_ID=coffee-faces
JWT_SECRET_KEY=$JWT_SECRET
API_URL=$API_URL
EOF

echo "📄 Created .env.$STAGE file for local testing"