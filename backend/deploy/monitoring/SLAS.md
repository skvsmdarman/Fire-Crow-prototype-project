# Fire Crow Service Level Agreements

## Uptime SLA

| Tier     | Monthly Uptime | Max Monthly Downtime | Credit |
|----------|---------------|---------------------|--------|
| Free     | 99.0%         | 7h 18m              | N/A    |
| Pro      | 99.5%         | 3h 39m              | 10%    |
| Enterprise | 99.9%       | 43m                  | 25%    |

## Performance SLA

| Metric                   | Target         | Measurement        |
|--------------------------|----------------|--------------------|
| API P50 response time    | < 200ms        | CloudWatch p50     |
| API P95 response time    | < 500ms        | CloudWatch p95     |
| API P99 response time    | < 2s           | CloudWatch p99     |
| Scan job completion (p95) | < 30 min      | DB job duration    |

## Availability SLA

| Component        | Expected Availability | Dependencies       |
|------------------|----------------------|--------------------|
| API endpoints    | 99.5%                | PostgreSQL, Redis  |
| Scan execution   | 99.0%                | API, Docker sandbox|
| File storage     | 99.9%                | Cloudflare R2/S3   |
| Web dashboard    | 99.5%                | API, PostgreSQL    |

## SLA Exclusions

- Scheduled maintenance (notified 72h in advance)
- Force majeure events
- Customer misconfiguration
- Third-party service outages (GitHub, Google, Cloudflare)
- Attack/abuse exceeding rate limits

## Monitoring & Alerting

- **Uptime checks**: Every 60 seconds via CloudWatch Synthetics
- **API response time**: CloudWatch alarms at p95 > 500ms
- **Error rate**: CloudWatch alarm at 5XX > 1% over 5 min
- **Certificate expiry**: 30-day warning via CloudWatch
- **Disk usage**: CloudWatch alarm at > 80%

## Incident Response

| Severity | Definition                | Response Time | Resolution Time |
|----------|---------------------------|---------------|-----------------|
| P0       | Complete outage           | 5 min         | 1 hour          |
| P1       | Major feature degradation | 15 min        | 4 hours         |
| P2       | Minor feature impacted    | 1 hour        | 8 hours         |
| P3       | Cosmetic / non-urgent     | 1 business day| Next release    |

## Backup & Recovery

- **Database**: Daily automated backups, 30-day retention (pro), 7-day (free)
- **Configuration**: Terraform state in S3 with versioning
- **Secrets**: AWS Secrets Manager with automatic rotation
- **Disaster Recovery**: Multi-AZ deployment, RTO < 1 hour, RPO < 5 min
