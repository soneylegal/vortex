# Cortex — Serverless Data Pipeline: Operations Manual

## 1. Architecture Overview

Cortex is a fully serverless event-driven data pipeline deployed on AWS. It ingests, transforms, and loads operational data from multiple sources into a centralized data lake for analytics and reporting.

### Core Components

| Component | Service | Purpose |
|-----------|---------|---------|
| Ingestion Gateway | API Gateway (REST) | Accepts incoming data payloads via HTTPS |
| Transform Engine | AWS Lambda (Python 3.12) | Stateless data transformation and validation |
| Event Bus | Amazon EventBridge | Routes events between pipeline stages |
| Storage Layer | Amazon S3 (data lake) | Stores raw and processed data in Parquet format |
| Metadata Store | Amazon DynamoDB | Tracks pipeline execution state and job metadata |
| Dead Letter Queue | Amazon SQS | Captures failed events for reprocessing |

### Data Flow

```
External Source → API Gateway → Lambda (Validate) → EventBridge
    → Lambda (Transform) → S3 (Processed)
    → DynamoDB (Metadata Update)
```

---

## 2. Common Errors and Troubleshooting

### Error 503 — Service Unavailable

**Symptoms:** API Gateway returns HTTP 503 to clients. Requests are not reaching the Lambda function.

**Root Causes:**
1. **Lambda concurrency exhaustion** — The account-level or function-level concurrency limit has been reached.
2. **API Gateway throttling** — The stage-level throttle limit (default: 10,000 RPS) has been exceeded.
3. **Regional service degradation** — AWS may be experiencing issues in the deployed region.

**Resolution Steps:**
1. Check Lambda concurrency metrics in CloudWatch:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name ConcurrentExecutions \
     --dimensions Name=FunctionName,Value=cortex-transform-engine \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 --statistics Maximum
   ```
2. If concurrency is maxed out, increase the reserved concurrency for the function:
   ```bash
   aws lambda put-function-concurrency \
     --function-name cortex-transform-engine \
     --reserved-concurrent-executions 200
   ```
3. Check API Gateway throttle settings in the AWS Console under **Stages → Settings → Default Method Throttling**.
4. If the issue is regional, check the [AWS Service Health Dashboard](https://health.aws.amazon.com/).

---

### Error 429 — Too Many Requests

**Symptoms:** API Gateway returns HTTP 429. Clients are being rate-limited.

**Root Causes:**
1. **Usage plan quota exceeded** — The API key has exhausted its daily/monthly quota.
2. **Burst limit reached** — Too many requests in a short time window (default burst: 5,000).

**Resolution Steps:**
1. Check current usage plan consumption:
   ```bash
   aws apigateway get-usage \
     --usage-plan-id <plan-id> \
     --key-id <api-key-id> \
     --start-date $(date -u +%Y-%m-%d) \
     --end-date $(date -u +%Y-%m-%d)
   ```
2. If legitimate traffic, increase the quota or burst limit in the Usage Plan settings.
3. If a DDoS or abuse pattern, enable AWS WAF on the API Gateway stage.

---

### Lambda Timeout Errors

**Symptoms:** Lambda functions are timing out (exceeding the configured 30-second limit). CloudWatch logs show `Task timed out after 30.00 seconds`.

**Root Causes:**
1. **Large payload processing** — Input data exceeds expected size, causing transformation to run longer.
2. **DynamoDB throttling** — Writes to the metadata store are being throttled due to insufficient provisioned capacity.
3. **Cold start penalty** — Functions deployed with large dependency layers experience 5-10 second cold starts.

**Resolution Steps:**
1. Check CloudWatch Logs for the specific invocation:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/cortex-transform-engine \
     --filter-pattern "Task timed out"
   ```
2. For large payloads, increase the Lambda timeout to 60 seconds:
   ```bash
   aws lambda update-function-configuration \
     --function-name cortex-transform-engine \
     --timeout 60
   ```
3. For DynamoDB throttling, switch to on-demand capacity mode:
   ```bash
   aws dynamodb update-table \
     --table-name cortex-pipeline-metadata \
     --billing-mode PAY_PER_REQUEST
   ```
4. For cold starts, enable Provisioned Concurrency:
   ```bash
   aws lambda put-provisioned-concurrency-config \
     --function-name cortex-transform-engine \
     --qualifier prod \
     --provisioned-concurrent-executions 5
   ```

---

### DynamoDB Write Failures

**Symptoms:** Pipeline metadata updates fail silently. Job status remains "IN_PROGRESS" indefinitely.

**Root Causes:**
1. **Conditional check failures** — An optimistic locking condition (`attribute_exists(job_id)`) is failing because the record doesn't exist yet.
2. **Item size exceeded** — The metadata payload exceeds the 400 KB DynamoDB item size limit.

**Resolution Steps:**
1. Enable DynamoDB Streams on the metadata table and set up a CloudWatch alarm for `SystemErrors`.
2. If the job record is missing, check whether the Validate Lambda successfully created the initial record.
3. For large items, store the detailed payload in S3 and keep only a reference in DynamoDB.

---

## 3. Lambda Function Restart Procedure

### Hot Restart (No Downtime)

Use this procedure to force Lambda to pick up new environment variables or configuration changes without redeploying code:

```bash
# Force a configuration update to cycle all warm instances
aws lambda update-function-configuration \
  --function-name cortex-transform-engine \
  --description "Hot restart - $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

This triggers a rolling refresh of all warm execution environments within ~60 seconds.

### Cold Restart (Full Redeployment)

Use this when code changes are required:

```bash
# Deploy new code from the CI/CD pipeline
make deploy STAGE=prod

# Verify the new version is active
aws lambda get-function \
  --function-name cortex-transform-engine \
  --query 'Configuration.LastModified'
```

---

## 4. API Gateway Configuration

### Stage Variables

| Variable | Production Value | Description |
|----------|-----------------|-------------|
| `TRANSFORM_FUNCTION` | `cortex-transform-engine` | Target Lambda function name |
| `LOG_LEVEL` | `WARNING` | Application log verbosity |
| `ENABLE_CACHING` | `true` | API Gateway response caching |
| `CACHE_TTL` | `300` | Cache TTL in seconds |

### CORS Configuration

CORS is enabled on all endpoints with the following headers:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, POST, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Authorization, X-Api-Key`

### Custom Domain

The production API is accessible at: `api.cortex.internal`  
Mapped to API Gateway stage `prod` via a Route 53 alias record.

---

## 5. Monitoring and Alerts

### CloudWatch Alarms

| Alarm | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| High Error Rate | Lambda Errors / Invocations | > 5% over 5 min | SNS → PagerDuty |
| Throttling | Lambda Throttles | > 10 in 1 min | SNS → Slack |
| High Latency | API Gateway Latency p99 | > 10s over 5 min | SNS → Slack |
| DLQ Depth | SQS ApproximateNumberOfMessages | > 50 | SNS → PagerDuty |

### Log Insights Queries

Find the slowest Lambda invocations:
```
fields @timestamp, @duration, @requestId
| filter @type = "REPORT"
| sort @duration desc
| limit 20
```

Find all errors in the last hour:
```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 50
```
