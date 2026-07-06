# Static Outbound IP Pool & Rate Limiting

To conduct authorized live website security audits without causing operational disruption or getting blocked by Web Application Firewalls (WAFs), Fire Crow uses a designated static outbound IP pool and strictly enforces rate-limiting rules.

---

## 1. Static Outbound IP Pool

When Fire Crow scans a verified live target, all requests originate from the following static IP addresses. You should whitelist these IPs in your firewall, intrusion detection systems (IDS), and WAF rules (e.g., Cloudflare, AWS WAF, or ModSecurity) to prevent scans from being blocked.

| Provider | Region | IP Addresses | Purpose |
|----------|--------|--------------|---------|
| AWS | us-east-1 | `192.0.2.50` | Primary active scanning engine |
| AWS | us-east-1 | `192.0.2.51` | Secondary scan runner (failover) |
| AWS | us-east-1 | `192.0.2.52` | Webhook notifications & integrations |

> [!NOTE]
> All outbound traffic is marked with the User-Agent header: `Mozilla/5.0 (compatible; FireCrow-Scanner/1.0; +https://fire-crow.onrender.com)`

---

## 2. Whitelist Configurations

### Cloudflare WAF
To allow Fire Crow traffic through Cloudflare:
1. Go to **Security > WAF > Tools**.
2. Under **IP Access Rules**, add the static IPs listed above.
3. Select the Action **Bypass** or **Allow** and apply it to **This Website** or **All Websites in Account**.

### AWS Security Groups / Network ACLs
Ensure your target instances allow inbound HTTP/HTTPS traffic from the static outbound IP range:
```yaml
Type: HTTP (80) & HTTPS (443)
Source: 192.0.2.50/32, 192.0.2.51/32
```

---

## 3. Active Scan Rate Limiting Rules

Fire Crow enforces a strict, polite scanning policy on verified live environments to avoid causing Denial of Service (DoS):

1. **Packet & Request Rate limits:**
   * **Nmap Port Scanning:** Max rate of 10 packets/second (`--max-rate 10`) using a polite timing template (`-T2`).
   * **Web Fuzzing & Exploitation:** A mandatory delay of `0.5s` is introduced between consecutive HTTP requests.
   * **Overall Limit:** Maximum of 15 requests per second (RPS) per verified target domain.

2. **Concurrency Limits:**
   * Only **one** active scan job can be running against any unique verified domain at any given time. Subsequent scan requests will be queued or rejected.

3. **Circuit Breaker Integration:**
   * If a target website responds with more than five consecutive `503 Service Unavailable` or `429 Too Many Requests` status codes, the active scanning engine automatically trips the circuit breaker, aborts the scan, and marks the job as paused or failed to protect the target.
