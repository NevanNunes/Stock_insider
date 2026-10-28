# Market Surveillance --- AWS Deployment and Cost Report

**Project:** Market Surveillance\
**Cloud provider:** Amazon Web Services (AWS)\
**Deployment region:** Asia Pacific (Mumbai), `ap-south-1`\
**Report status:** Deployment record based on the implementation and
console checks described during deployment\
**Prepared:** 28 October 2026

> **Accuracy note:** This report documents the architecture, settings,
> successful checks, and troubleshooting recorded during deployment.
> Where exact values were not confirmed (for example, the RDS instance
> class, allocated storage, or final billing period), they are
> explicitly marked as needing verification rather than guessed. AWS
> console values and charges can change over time.

------------------------------------------------------------------------

## 1. Executive Summary

Market Surveillance is a web application deployed on AWS with a
frontend, a FastAPI backend, a managed PostgreSQL database, and
supporting AWS services for configuration, messaging, storage, logging,
monitoring, and load balancing.

The backend runs on an EC2 instance rather than being entirely
serverless. Nginx serves the built frontend and reverse-proxies API
requests to the backend. Amazon RDS for PostgreSQL stores application
data. AWS Systems Manager Parameter Store supplies application
configuration and secrets at runtime. Amazon S3 stores report/object
files, Amazon SQS provides a queue for trade-processing work, and Amazon
SNS sends alert notifications. CloudWatch collects backend logs and
monitors EC2 CPU utilization.

An Application Load Balancer (ALB) fronts the application. An EC2 launch
template was created from an Amazon Machine Image (AMI) of the working
server, and an Auto Scaling Group (ASG) was attached to the existing ALB
target group. At the last recorded check, the ASG had desired capacity 1
and one healthy managed instance; the target group had two healthy
targets, because the original EC2 instance was still running separately.

The application health endpoint returned HTTP 200 and a JSON health
response identifying the production environment and AWS integration
modes. The frontend production build completed successfully. S3
upload/download, SQS processing, and SNS email alert behavior were also
exercised during deployment.

------------------------------------------------------------------------

## 2. Application Overview

### 2.1 Purpose

The application is called **Market Surveillance**. Its deployment
includes a backend API and frontend, a PostgreSQL database, and
asynchronous processing/alerting integrations. The project name, service
names, and resource names use the `market-surveillance` prefix.

### 2.2 Application components

  -----------------------------------------------------------------------
  Component               Technology / AWS        Role
                          service                 
  ----------------------- ----------------------- -----------------------
  Frontend                React + Vite production Browser-based user
                          build                   interface

  Web server / reverse    Nginx on EC2            Serves static frontend
  proxy                                           assets and proxies API
                                                  traffic

  Backend API             FastAPI / Python        Application API and
                                                  business logic

  Compute                 Amazon EC2, `t3.small`  Runs the backend and
                          launch template         Nginx-hosted
                                                  application

  Database                Amazon RDS for          Persists application
                          PostgreSQL              records

  Runtime configuration   AWS Systems Manager     Supplies configuration
  and secrets             Parameter Store         without embedding
                                                  credentials in source
                                                  code

  Object/file storage     Amazon S3               Stores report and file
                                                  objects

  Work queue              Amazon SQS              Queues trade-processing
                                                  messages

  Notifications           Amazon SNS              Publishes alert
                                                  notifications,
                                                  including email
                                                  delivery through a
                                                  subscribed endpoint

  Traffic distribution    Application Load        Routes HTTP requests to
                          Balancer (ALB)          healthy application
                                                  targets

  Instance lifecycle      EC2 Auto Scaling        Maintains desired
                                                  capacity and can scale
                                                  based on CPU target
                                                  tracking

  Logs and metrics        Amazon CloudWatch +     Collects backend logs
                          CloudWatch Agent        and monitors compute
                                                  health

  Access control          IAM role and policies   Grants EC2
                                                  application/agent
                                                  permissions to AWS
                                                  services

  Network isolation       VPC, public/private     Defines network
                          subnets, route tables,  placement and access
                          security groups,        rules
                          Internet Gateway        

  Cost management         AWS Budgets / Cost      Tracks cost and
                          Explorer                provides budget
                                                  notifications
  -----------------------------------------------------------------------

### 2.3 Important application behavior observed

The local backend health endpoint and the public ALB endpoint both
returned HTTP 200. The health response was:

``` json
{
  "status": "ok",
  "app": "MarketSurveillanceAPI",
  "env": "production",
  "sqs_mode": "aws",
  "sns_mode": "aws",
  "s3_mode": "aws"
}
```

This response confirmed that the API was running in the production
environment and configured to use AWS modes for SQS, SNS, and S3. It
does not, by itself, prove that every operation in each integration will
always succeed; the additional checks described later provide separate
evidence.

------------------------------------------------------------------------

## 3. AWS Region, Naming, and Resource Inventory

**Region:** `ap-south-1` (Asia Pacific --- Mumbai)\
**AWS account ID recorded during deployment:** `925126087009`

Resource names and identifiers recorded in the deployment:

  --------------------------------------------------------------------------------------------------------------------------
  Resource                Name / identifier                                                    Notes
  ----------------------- -------------------------------------------------------------------- -----------------------------
  VPC                     `market-surveillance-vpc`                                            VPC ID
                                                                                               `vpc-007091a9370a62500`; CIDR
                                                                                               not restated here

  Public subnet A         `market-surveillance-public-a`                                       `subnet-0fc25e569888824c9`,
                                                                                               `10.0.1.0/24`, `ap-south-1a`

  Public subnet B         `market-surveillance-public-b`                                       `subnet-0b564aadfb6e568e9`,
                                                                                               `10.0.2.0/24`, `ap-south-1b`

  Private subnet A        `market-surveillance-private-a`                                      `subnet-0ee3584bdbb2d9d7b`,
                                                                                               `10.0.11.0/24`, `ap-south-1a`

  Private subnet B        `market-surveillance-private-b`                                      `subnet-0eec2e092f09f31b2`,
                                                                                               `10.0.12.0/24`, `ap-south-1b`

  Original EC2 instance   `i-03ec7d6c6282c4ede`                                                Working instance used to
                                                                                               create the AMI

  Auto Scaling EC2        `i-0703e529d317ee3a8`                                                Launched by ASG; its security
  instance                                                                                     group was corrected after a
                                                                                               target timeout

  EC2 instance type       `t3.small`                                                           Confirmed for the launch
                                                                                               template

  EC2 IAM role            `MarketSurveillanceEC2Role`                                          Instance role used for AWS
                                                                                               access

  Application Load        `market-surveillance-alb`                                            Public DNS recorded below
  Balancer                                                                                     

  ALB DNS name            `market-surveillance-alb-1862821985.ap-south-1.elb.amazonaws.com`    HTTP endpoint tested; do not
                                                                                               assume HTTPS was configured

  Target group            `market-surveillance-tg`                                             Used by the existing ALB and
                                                                                               ASG

  AMI                     `market-surveillance-v1`                                             Created from the working EC2
                                                                                               instance; AMI reached
                                                                                               `Available`

  Launch template         `market-surveillance-lt`                                             Default version described as
                                                                                               "Market Surveillance
                                                                                               production v1"

  Auto Scaling Group      `market-surveillance-asg`                                            Desired 1, minimum 1, maximum
                                                                                               2

  RDS endpoint            `market-surveillance-db.c1e60ssokxno.ap-south-1.rds.amazonaws.com`   PostgreSQL database named
                                                                                               `postgres`

  S3 bucket               `market-surveillance-reports-925126087009`                           Used for report/object
                                                                                               storage tests

  SQS queue               `market-surveillance-trades`                                         Queue URL listed in
                                                                                               configuration

  SNS topic               `market-surveillance-alerts`                                         Used for suspicious-trade
                                                                                               alert notifications

  CloudWatch log group    `/market-surveillance/prod/backend`                                  Backend log group; retention
                                                                                               7 days

  CloudWatch alarm        `MarketSurveillance-High-CPU`                                        EC2 CPUUtilization average
                                                                                               above 80% over a 5-minute
                                                                                               period

  Parameter Store prefix  `/market-surveillance/prod/`                                         Runtime configuration prefix

  AWS region parameter    `ap-south-1`                                                         Region used by application
                                                                                               integrations
  --------------------------------------------------------------------------------------------------------------------------

### 3.1 Network design

The custom VPC has two public subnets across two Availability Zones and
two private subnets across the same zones. The Auto Scaling Group was
configured to use the two public subnets:

-   `market-surveillance-public-a` in `ap-south-1a`
-   `market-surveillance-public-b` in `ap-south-1b`

The private subnets were present in the VPC but were not selected for
this initial Auto Scaling Group. The intended security design is for
public ALB traffic to reach the application instance only through the
ALB security group, while the database remains protected by its own
security group and is reachable from the application tier. Verify actual
route tables and inbound rules in the AWS console before claiming every
network rule has been audited.

The Auto Scaling instance initially launched with the `default` security
group instead of `market-surveillance-ec2-sg`. This caused the target
group health check on port 80 to time out. The security group on the
running instance was changed to the application security group;
afterward, both target group entries reported healthy. The launch
template was **not** updated afterward, so a future replacement may
again receive the wrong security group unless the launch template is
corrected.

------------------------------------------------------------------------

## 4. Deployment Architecture and Request Flow

### 4.1 Request path

1.  A user opens the ALB's public DNS name over HTTP.
2.  The Application Load Balancer forwards the request to a healthy
    registered target in `market-surveillance-tg`.
3.  The EC2 instance receives the request through Nginx on port 80.
4.  Nginx serves the built React/Vite files for frontend routes.
5.  API requests are reverse-proxied to FastAPI on `127.0.0.1:8000`.
6.  The backend accesses PostgreSQL on RDS for persistent application
    data.
7.  The backend uses Parameter Store for runtime configuration, S3 for
    objects/reports, SQS for asynchronous trade work, and SNS for alert
    notifications.
8.  The CloudWatch Agent ships the backend log file to CloudWatch Logs;
    CloudWatch monitors EC2 CPU and evaluates the configured alarm.

### 4.2 High-level diagram

``` text
Browser
   |
   | HTTP
   v
Application Load Balancer
market-surveillance-alb
   |
   v
Target group: market-surveillance-tg
   |
   +---------------------------+
   |                           |
   v                           v
Original EC2                 Auto Scaling EC2
Nginx :80                    Nginx :80
FastAPI 127.0.0.1:8000       FastAPI 127.0.0.1:8000
   |                           |
   +-------------+-------------+
                 |
       +---------+----------+-----------------+
       |                    |                 |
       v                    v                 v
  RDS PostgreSQL      SQS trade queue     S3 reports
                            |
                            v
                     Backend worker
                            |
                            v
                       SNS alerts

EC2 backend.log -> CloudWatch Agent -> CloudWatch Logs
EC2 CPU metrics -> CloudWatch alarm
Parameter Store -> runtime application configuration
```

**Architecture caveat:** This is a conceptual diagram. The original EC2
instance and the ASG-managed instance were both registered as targets
and healthy at the last check. The original instance was not yet retired
or transferred into the ASG.

------------------------------------------------------------------------

## 5. Frontend Deployment

The frontend uses React and Vite. The production build was executed
from:

``` bash
cd /opt/market-surveillance/frontend
npm run build
```

The build completed successfully with Vite `6.4.4`:

``` text
vite v6.4.4 building for production...
✓ 2265 modules transformed.
dist/index.html 0.91 kB
dist/assets/index-DDWups1A.css 15.10 kB
dist/assets/index-B7bpznly.js 725.83 kB
✓ built in 9.08s
```

A non-fatal warning indicated that a JavaScript chunk exceeded 500 kB.
The build still succeeded. Potential future optimization includes
route-based code splitting and reviewing large dependencies, but this
was not required to get the application working.

Nginx was configured with the frontend production directory:

``` nginx
root /opt/market-surveillance/frontend/dist;
try_files $uri $uri/ /index.html;
```

This supports static file delivery and frontend client-side routes.
After rebuilding the frontend, a browser hard refresh was recommended to
avoid stale cached assets.

------------------------------------------------------------------------

## 6. Backend Deployment and Service Management

The backend project directory is:

``` text
/opt/market-surveillance/backend
```

The Python virtual environment is:

``` text
/opt/market-surveillance/backend/venv
```

The backend is managed by the `market-surveillance` systemd service. It
binds to localhost port 8000:

``` text
127.0.0.1:8000
```

Nginx acts as the public-facing web server and reverse proxy, so the
FastAPI process does not need to bind directly to a public interface.

Useful operational commands used or relevant to this deployment:

``` bash
sudo systemctl status market-surveillance
sudo systemctl restart market-surveillance
curl -i http://127.0.0.1:8000/api/health
```

The health check returned HTTP 200 locally. The ALB endpoint also
returned HTTP 200.

### 6.1 Backend logging

A systemd drop-in was configured at:

``` text
/etc/systemd/system/market-surveillance.service.d/override.conf
```

with:

``` ini
[Service]
StandardOutput=append:/var/log/market-surveillance/backend.log
StandardError=append:/var/log/market-surveillance/backend.log
```

The backend log file is:

``` text
/var/log/market-surveillance/backend.log
```

------------------------------------------------------------------------

## 7. Database Deployment and Schema Correction

The application uses Amazon RDS for PostgreSQL.

Recorded connection details:

-   Endpoint:
    `market-surveillance-db.c1e60ssokxno.ap-south-1.rds.amazonaws.com`
-   Database name: `postgres`
-   Region: `ap-south-1`

Database credentials are intended to be retrieved from Systems Manager
Parameter Store, not hard-coded into application source code.

### 7.1 Initial database seeding

The backend's seeder is located at:

``` text
/opt/market-surveillance/backend/app/db/seeder.py
```

During startup, logs confirmed that database tables were created or
verified and the seeder ran from `/opt/market-surveillance/data`. The
seeder reported that default demo users were initialized or already
present and that seeding completed. The seeder adds baseline data only
when relevant tables are empty and initializes demo users when they are
absent.

The application included a demo admin login used during testing. Demo
credentials should be treated as temporary demonstration credentials and
changed or disabled before any real-world deployment. Credentials are
intentionally not repeated in this report.

### 7.2 Schema mismatch discovered and fixed

After application code changes, startup initially failed because the
database schema did not match the ORM models:

``` text
sqlalchemy.exc.ProgrammingError: column trader_accounts.user_id does not exist
```

The ORM model expected: - `trader_accounts.user_id`, an optional integer
foreign key to `users.id` - `users.trader_id`, an optional `VARCHAR(16)`
field

The database was updated with additive, non-destructive changes:

``` sql
ALTER TABLE trader_accounts
ADD COLUMN IF NOT EXISTS user_id INTEGER NULL REFERENCES users(id);

ALTER TABLE users
ADD COLUMN IF NOT EXISTS trader_id VARCHAR(16) NULL;
```

The checks afterward confirmed that both columns existed. The service
was restarted and subsequently reported successful startup, database
seeding, worker startup, and application startup completion.

This fix resolved the specific missing-column issue. A more mature
deployment should use a versioned database migration system so schema
changes are reproducible and tracked.

------------------------------------------------------------------------

## 8. Systems Manager Parameter Store and IAM

### 8.1 Runtime configuration

The application was configured to use AWS Systems Manager Parameter
Store:

``` text
USE_PARAMETER_STORE=true
Parameter prefix: /market-surveillance/prod/
AWS region: ap-south-1
```

The configuration includes database settings (host, port, database name,
username and password), an application secret key, AWS region, SQS queue
URL, SNS topic ARN, and S3 bucket name.

This approach keeps sensitive runtime values out of source code and lets
the EC2 role retrieve only the required parameters. The application
should never log secret values or expose them to the frontend.

### 8.2 EC2 IAM role

The EC2 instance profile uses the IAM role:

``` text
MarketSurveillanceEC2Role
```

The assumed role was observed as:

``` text
arn:aws:sts::925126087009:assumed-role/MarketSurveillanceEC2Role/i-03ec7d6c6282c4ede
```

The role grants application access to relevant AWS services. It also
includes permissions for CloudWatch Logs publishing. The role was
intended to follow least-privilege principles, although the final scope
of every policy should be reviewed against the current application
behavior before a formal security audit.

An inline policy named `MarketSurveillanceCloudWatchLogsPolicy` grants
the log agent actions including `logs:CreateLogStream`,
`logs:PutLogEvents`, and `logs:DescribeLogStreams` on the backend log
group, plus `logs:DescribeLogGroups` on `*`.

No AWS access keys should be hard-coded in the application. The EC2
instance role is the intended mechanism for AWS API authentication.

------------------------------------------------------------------------

## 9. Amazon S3 Integration

The S3 bucket used for reports and objects is:

``` text
market-surveillance-reports-925126087009
```

An integration test uploaded and downloaded the object:

``` text
reports/integration-test.txt
```

The object was encrypted using S3 server-side encryption with AES-256
(SSE-S3). Upload and download succeeded.

A delete attempt was denied because the EC2 role did not have
`s3:DeleteObject` permission. This is consistent with a restricted
permission policy, but it left the test object in the bucket at the time
of the check. The local temporary files used in the test may also have
remained on the instance.

**Cleanup note:** Remove the test object through the S3 console if it is
no longer needed. Do not broaden the application's IAM permissions
solely to delete a test object unless delete functionality is a
legitimate application requirement.

------------------------------------------------------------------------

## 10. Amazon SQS Integration

The SQS queue is named:

``` text
market-surveillance-trades
```

Its queue URL was stored in Parameter Store. Configuration details
recorded during setup:

-   Server-side encryption enabled
-   Long polling: 10 seconds
-   Message retention: 24 hours
-   Visibility timeout: 60 seconds
-   No dead-letter queue was configured at the time of setup

A test message was consumed by the worker. The test payload lacked a
`trade_id`, so the worker logged that it was missing. This showed that
the polling/consumption path was active, while also demonstrating that
the message schema should be validated.

Startup logs showed:

``` text
SQS Worker started — polling every 0.5s
```

Real trade messages were subsequently enqueued and processed. For
production-grade reliability, define a dead-letter queue, validate
message payloads, use idempotent processing, and ensure visibility
timeout exceeds the expected processing duration.

**Auto Scaling caveat:** Each AMI-based EC2 instance may start its own
SQS worker. If the ASG scales to two instances, multiple workers may
poll the same queue. SQS distributes messages among consumers, but
application processing should be safe under concurrency and idempotent.
If the web tier and worker need different scaling behavior, consider
separating them into distinct services or groups.

------------------------------------------------------------------------

## 11. Amazon SNS Alerting

The SNS topic is:

``` text
market-surveillance-alerts
```

Topic ARN:

``` text
arn:aws:sns:ap-south-1:925126087009:market-surveillance-alerts
```

The EC2 role has publish permission for the topic. A suspicious-trade
scenario triggered an email notification, and backend logs indicated
that the SNS notification was sent. This provided practical evidence
that the alert publishing path worked.

The role did not have permission to retrieve all SNS topic attributes,
so `get-topic-attributes` was denied. This did not prevent the
application's publish behavior from working.

------------------------------------------------------------------------

## 12. CloudWatch Logging, Monitoring, and Alarm

### 12.1 CloudWatch Agent

The CloudWatch Agent version installed was:

``` text
1.300074.0b1920
```

The agent was enabled and active. Its configuration file was:

``` text
/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
```

It was configured to ship:

``` text
/var/log/market-surveillance/backend.log
```

to the CloudWatch log group:

``` text
/market-surveillance/prod/backend
```

The log stream naming pattern used the instance ID and `backend`. Log
retention was set to **7 days**. Agent logs showed successful publishing
and no new permissions errors at the final check.

### 12.2 CPU alarm

A CloudWatch alarm named:

``` text
MarketSurveillance-High-CPU
```

was created with the following recorded settings:

-   Metric: EC2 `CPUUtilization`
-   Statistic: Average
-   Threshold: greater than 80%
-   Period: 5 minutes
-   SNS topic configured for notifications
-   State at the recorded check: `OK`

This alarm provides an operational signal if CPU usage becomes high. It
is separate from the ASG target-tracking policy, which was configured to
maintain average CPU utilization around 60%.

------------------------------------------------------------------------

## 13. Application Load Balancer (ALB)

The existing ALB is named:

``` text
market-surveillance-alb
```

Recorded DNS name:

``` text
market-surveillance-alb-1862821985.ap-south-1.elb.amazonaws.com
```

Target group:

``` text
market-surveillance-tg
```

The public HTTP health endpoint returned HTTP 200 through the ALB. The
available deployment notes confirm HTTP behavior; they do not establish
that an HTTPS listener or TLS certificate was configured.

The ALB was configured to use the target group that later became
attached to the Auto Scaling Group. At the final recorded check, two
targets were registered and both were healthy.

### 13.1 Target health troubleshooting

After the ASG created its instance, the target group showed two
registered targets: - one healthy - one unhealthy with a request timeout

The unhealthy target was:

``` text
i-0703e529d317ee3a8
```

It was running and had passed EC2 status checks. Inspection showed it
had the `default` security group instead of
`market-surveillance-ec2-sg`. The security group was changed on the
running instance. After the change and refresh, both targets were
reported healthy.

This was a security-group reachability problem, not an EC2 system
status-check failure.

**Outstanding issue:** The launch template was not updated after this
correction. It should be updated to use `market-surveillance-ec2-sg`
before relying on future replacement launches. If a new instance is
launched from the current template, the wrong security group may be
attached again.

------------------------------------------------------------------------

## 14. Auto Scaling Configuration

### 14.1 AMI and launch template

An AMI named `market-surveillance-v1` was created from the working EC2
instance. The AMI reached the `Available` state.

The launch template is:

``` text
market-surveillance-lt
```

Recorded settings: - AMI: `market-surveillance-v1` - Instance type:
`t3.small` - IAM instance profile: `MarketSurveillanceEC2Role` - Version
description: `Market Surveillance production v1`

The launch template was confirmed to use the intended instance type and
IAM instance profile. However, its security-group configuration did not
match the intended application security group on the instance that
launched, as described above.

### 14.2 Auto Scaling Group

The group is named:

``` text
market-surveillance-asg
```

Recorded settings:

  Setting                          Value
  -------------------------------- --------------------------------------------------------
  Launch template                  `market-surveillance-lt`
  VPC                              `market-surveillance-vpc`
  Subnets                          Public A and public B
  Desired capacity                 1
  Minimum capacity                 1
  Maximum capacity                 2
  Scaling policy                   Target tracking
  Target metric                    Average CPU utilization
  Target value                     60%
  Health-check grace period        300 seconds
  Availability Zone distribution   Balanced best effort
  Instance maintenance policy      No policy
  Tags                             `Project=MarketSurveillance`, `Environment=Production`
  Load balancer                    `market-surveillance-alb`
  Target group                     `market-surveillance-tg`

The ASG reported one instance and the instance was healthy. The target
group reported two healthy targets because the original EC2 instance was
still running separately. Thus, the ASG was not yet the sole manager of
all targets.

### 14.3 What Auto Scaling does and does not guarantee

The target-tracking policy is configured to adjust desired capacity to
maintain average CPU near 60%, bounded by minimum 1 and maximum 2. This
does not prove that scale-out has been exercised under load. To
demonstrate scale-out, generate suitable load in a controlled test and
observe the ASG activity history, instance count, and target health.

Auto Scaling itself does not incur a separate fee, but additional EC2
instances and related resources do incur charges.

### 14.4 Production-hardening considerations

Before relying on this configuration beyond a short demonstration:

1.  Update the launch template with `market-surveillance-ec2-sg`.
2.  Set the ASG to use the corrected launch template version.
3.  Confirm the AMI boots correctly and that the app starts after a
    fresh launch.
4.  Consider moving application instances into private subnets, with ALB
    in public subnets and appropriate outbound access (for example, NAT
    or VPC endpoints) if the design and budget allow.
5.  Ensure the ALB security group is the only permitted source for
    application HTTP traffic.
6.  Ensure database access is restricted to the application tier.
7.  Test replacement behavior and health checks.
8.  Consider how multiple instances running the SQS worker interact.
9.  Use HTTPS for real users and avoid using demonstration credentials
    in production.

------------------------------------------------------------------------

## 15. Verification and Test Results

The following checks were recorded during deployment:

  --------------------------------------------------------------------------------
  Test                    Result                  Evidence / notes
  ----------------------- ----------------------- --------------------------------
  Backend systemd service Passed after schema     `market-surveillance`
                          correction              active/running

  Local API health        Passed                  HTTP 200 at
  endpoint                                        `127.0.0.1:8000/api/health`

  Public ALB health       Passed                  HTTP 200
  endpoint                                        

  Frontend production     Passed                  Vite build completed
  build                                           successfully

  Database startup and    Passed after schema     Startup logs showed tables
  seeding                 correction              verified and seeding complete

  Database schema columns Passed                  `trader_accounts.user_id` and
                                                  `users.trader_id` existed after
                                                  ALTER TABLE

  S3 upload               Passed                  Test object uploaded

  S3 download             Passed                  Test object downloaded

  S3 delete               Denied                  Role lacked `s3:DeleteObject`;
                                                  test object may remain

  SQS polling/consumption Passed with             Worker consumed test message;
                          test-message caveat     payload lacked `trade_id`

  SNS alert               Passed in test          Suspicious-trade email received;
                                                  logs indicated notification sent

  CloudWatch log shipping Passed at last check    Agent active and log publishing
                                                  observed

  CloudWatch CPU alarm    Created                 `MarketSurveillance-High-CPU`,
                                                  state `OK` at check

  ASG launch              Passed                  ASG desired capacity 1, one
                                                  instance healthy

  ALB target health after Passed                  Two targets reported healthy
  SG fix                                          

  ASG scale-out under     Not confirmed           Policy configured, but a
  load                                            controlled scale-out test was
                                                  not recorded

  Fresh-instance          Not confirmed           Launch template still needs SG
  replacement using                               correction
  corrected SG                                    
  --------------------------------------------------------------------------------

------------------------------------------------------------------------

## 16. Cost Analysis

### 16.1 Cost Explorer snapshot

The AWS Cost Explorer screenshot taken on **28 October 2026** showed the
following costs for October 2026 as displayed in the dashboard:

  Service                                           Displayed October cost (USD)
  ----------------------------------------------- ------------------------------
  Amazon Relational Database Service                                      \$0.66
  Amazon EC2 --- Compute                                                  \$0.22
  Amazon Elastic Load Balancing                                           \$0.10
  Amazon Virtual Private Cloud                                            \$0.09
  EC2 --- Other                                                           \$0.02
  Others                                                                  \$0.00
  **Approximate total of displayed categories**                       **\$1.09**

The total is the sum of the rounded category values visible in the
screenshot. The exact unrounded total may differ. These figures
represent the dashboard's October-to-date display, not a final monthly
invoice. Billing data may lag, and additional charges can appear later.

### 16.2 Interpreting the cost categories

-   **RDS --- \$0.66:** Largest visible category. Likely reflects
    database compute and/or associated RDS usage. The exact instance
    class, storage configuration, backup usage, and detailed line items
    were not captured in the recorded notes and must be checked in RDS
    and Cost Explorer.
-   **EC2 compute --- \$0.22:** EC2 instance runtime. With the original
    instance and an ASG-managed instance both running, compute costs can
    rise compared with running only one instance.
-   **Elastic Load Balancing --- \$0.10:** Cost of operating the ALB and
    its usage. The ALB can continue to incur charges during idle
    periods.
-   **VPC --- \$0.09:** May include networking-related billable items
    such as public IPv4 address usage. The screenshot category alone is
    insufficient to identify the exact line item.
-   **EC2 Other --- \$0.02:** May include EBS volumes or other
    EC2-associated charges. Inspect the detailed billing view to
    confirm.

### 16.3 Simple projection (illustrative only)

If the displayed total of approximately **\$1.09** represented 28
complete days of comparable usage, a straight-line projection would be:

-   Average per day: `$1.09 / 28 ≈ $0.039`
-   Approximate 30-day projection: `$0.039 × 30 ≈ $1.17`

**This is not a dependable bill forecast.** It assumes 28 days of
representative usage, while the infrastructure changed during the month
and the Auto Scaling Group was recently added. Actual charges depend on
resource uptime, usage, region-specific pricing, storage, networking,
and billing-data delays. Use AWS Cost Explorer and the AWS Pricing
Calculator for a more accurate estimate.

### 16.4 Cost risks

1.  **A second EC2 instance:** The original EC2 instance and ASG
    instance were both running at the last check. The ASG desired
    capacity of 1 does not include the original instance because it is
    not managed by that ASG.
2.  **Scale-out:** The ASG can launch a second managed instance when the
    policy calls for it, increasing compute costs.
3.  **RDS:** The database can continue charging while available, even
    when there is little application traffic.
4.  **ALB:** The load balancer may continue charging while it exists.
5.  **Storage and addresses:** EBS volumes, snapshots, S3 data, public
    IPv4 addresses, logs, and backups can create additional charges.
6.  **Data transfer and requests:** S3, network transfer, queue/API
    usage, and logging can incur usage-dependent costs.
7.  **Incomplete cleanup:** Stopping EC2 alone does not necessarily stop
    charges for EBS, RDS storage, ALB, public IPv4 addresses, snapshots,
    or other retained resources.

### 16.5 Cost-control recommendations

For a short project demonstration:

-   Keep ASG desired capacity at 1 and maximum capacity at 2 unless
    scale-out is being demonstrated.
-   Avoid generating unnecessary load that triggers scale-out.
-   Keep the original instance until the ASG instance and ALB path have
    been tested; do not remove the working deployment prematurely.
-   Review RDS instance class, storage, backups, and current status in
    the RDS console.
-   Inspect Cost Explorer by service and usage type, not just by
    high-level service category.
-   Keep the existing AWS Budget alert enabled.
-   Use tags to identify resources belonging to the project.
-   After the demonstration, perform a planned cleanup of resources that
    are no longer needed.
-   Re-check Cost Explorer and Billing after cleanup because cost data
    can lag.

### 16.6 Budget alert

A monthly AWS Budget of **\$1** was configured, with notifications. The
budget is a warning mechanism; it does not automatically stop EC2, RDS,
the ALB, or other resources. If costs exceed the threshold, action is
still required.

### 16.7 Official cost tools

-   AWS Pricing Calculator: <https://calculator.aws/>
-   AWS Cost Explorer: available from the AWS Billing and Cost
    Management console.
-   AWS Budgets: available from the AWS Billing and Cost Management
    console.

Use the calculator with region `ap-south-1` and the actual
instance/database types, hours, storage, load balancer, and public IPv4
usage. Do not assume a Free Tier benefit or credit covers every resource
or usage category.

------------------------------------------------------------------------

## 17. Security and Operational Considerations

### Positive controls implemented

-   Runtime configuration and secrets are retrieved through Parameter
    Store.
-   EC2 uses an IAM role rather than embedded AWS access keys.
-   S3 objects were uploaded with server-side encryption.
-   CloudWatch logging and a CPU alarm were configured.
-   The application server's public HTTP path is fronted by an ALB.
-   The S3 delete operation was denied under the current role policy,
    illustrating that permissions are restricted.

### Items to review

-   Confirm all security groups and their rules, especially ALB-to-EC2
    port 80 and EC2-to-RDS database access.
-   Correct the launch template's security group before relying on
    instance replacement.
-   Confirm whether HTTPS is configured; the recorded public health test
    used HTTP.
-   Change demonstration credentials and rotate any secrets that may
    have been exposed during development.
-   Avoid storing secrets in AMIs, shell history, logs, or source
    control.
-   Review IAM permissions for least privilege.
-   Add an SQS dead-letter queue and idempotent processing for
    production-grade reliability.
-   Review RDS backups and deletion protection in accordance with the
    demo's lifecycle.
-   Set log retention intentionally and remember that CloudWatch Logs
    storage can incur charges.
-   Verify the S3 test object and local temporary files are removed if
    no longer needed.

------------------------------------------------------------------------

## 18. Known Limitations and Outstanding Items

The following are known from the deployment record and should not be
represented as completed unless subsequently verified:

1.  **Launch template security group:** Not updated after correcting the
    running instance. Future launches may again attach the default
    security group.
2.  **ASG replacement test:** No recorded confirmation that a fresh
    replacement launched from the corrected template will become
    healthy.
3.  **Scale-out test:** Target tracking is configured, but scale-out
    under load was not demonstrated in the recorded checks.
4.  **HTTPS:** The recorded public endpoint test was HTTP. TLS/HTTPS
    setup is not confirmed.
5.  **RDS details:** Exact instance class, allocated storage, Multi-AZ
    setting, backup retention, and deletion protection were not
    captured.
6.  **Billing forecast:** The \$1.09 amount is an October-to-date Cost
    Explorer snapshot, not a final monthly bill.
7.  **S3 test object:** Delete was denied; the test object may still
    exist.
8.  **SQS dead-letter queue:** None was configured at the time of setup.
9.  **Worker duplication:** Each ASG instance may run a queue worker;
    concurrency behavior should be tested.
10. **Full cleanup:** Resources have not yet been deleted. Cleanup must
    include associated billable resources, not just EC2 instances.

------------------------------------------------------------------------

## 19. Suggested Demonstration Plan

A concise demonstration can follow this order:

1.  Open the application through the ALB DNS name and show the working
    frontend.
2.  Demonstrate a key application workflow using seeded/demo data.
3.  Show the API health endpoint returning HTTP 200.
4.  Show the RDS database resource and explain that application data is
    stored in a managed PostgreSQL database.
5.  Show Parameter Store parameter names/prefix without exposing
    parameter values or secrets.
6.  Show the S3 bucket and the report/object storage use case.
7.  Show the SQS queue and explain asynchronous trade processing.
8.  Demonstrate the SNS email alert triggered by a suspicious-trade
    scenario, if safe test data is available.
9.  Show the CloudWatch backend log group and
    `MarketSurveillance-High-CPU` alarm.
10. Show the ALB target group with two healthy targets.
11. Show the Auto Scaling Group settings (minimum 1, desired 1, maximum
    2, target CPU 60%).
12. Explain that target tracking is configured; only claim that
    scale-out was tested if you actually observe it launching a new
    instance during a controlled test.
13. Show the Cost Explorer snapshot and describe the cost-control
    approach.

Do not display secrets, database passwords, JWTs, access tokens, or full
sensitive parameter values during the demonstration.

------------------------------------------------------------------------

## 20. Post-Demonstration Cleanup Checklist

Perform cleanup only after the demonstration and after confirming that
no further access to the application is required. Resource dependencies
matter, so use the AWS console and verify each resource's state after
deletion.

### Suggested order

1.  Record any screenshots and evidence needed for the report.
2.  Decide whether the application must remain available during any
    evaluation period.
3.  Set the ASG desired capacity to zero or delete the ASG when ready to
    stop managed instances.
4.  Delete the Auto Scaling Group if it is no longer needed.
5.  Deregister or remove any remaining target registrations as
    appropriate.
6.  Delete the ALB if it is no longer required.
7.  Delete the target group if it is no longer required and no longer in
    use.
8.  Terminate the original EC2 instance after verifying that it is no
    longer needed.
9.  Delete unused launch templates and deregister the AMI; remove
    associated EBS snapshots if they are no longer required.
10. Delete the RDS database only after deciding that its data is no
    longer needed. Review final snapshot choices carefully; snapshots
    can continue to incur storage costs.
11. Delete S3 test objects and any bucket contents that are no longer
    needed. Empty the bucket before deleting it.
12. Delete the SQS queue and SNS topic if they are no longer needed.
13. Remove project-specific Parameter Store parameters if they are no
    longer required.
14. Remove project-specific CloudWatch alarms and log groups if no
    longer required.
15. Review EBS volumes, snapshots, Elastic IPs, public IPv4 usage, NAT
    gateways, VPC endpoints, and other network resources that may remain
    billable.
16. Delete security groups, subnets, route tables, Internet Gateway, and
    VPC only after dependent resources are removed and AWS permits
    deletion.
17. Check AWS Budgets and Cost Explorer after cleanup. Allow for billing
    data delays and re-check later.

**Do not delete resources in this list blindly.** Confirm resource
ownership, dependencies, data-retention needs, and whether any shared
resources are used by another project.

------------------------------------------------------------------------

## 21. Conclusion

Market Surveillance was deployed as a multi-tier AWS application with a
React/Vite frontend, Nginx, FastAPI, RDS PostgreSQL, Parameter Store,
S3, SQS, SNS, CloudWatch, an Application Load Balancer, and an Auto
Scaling Group. The application was brought to a working state after
resolving a database schema mismatch, rebuilding the frontend,
confirming backend health, testing storage and messaging integrations,
and correcting a security-group issue that initially caused an ALB
target health-check timeout.

At the final recorded check, the backend health endpoint returned HTTP
200, the frontend build succeeded, the ASG maintained one healthy
managed instance, and both target-group entries were healthy. The
deployment includes basic monitoring, a CPU alarm, and a budget
notification. The Cost Explorer screenshot showed approximately \$1.09
in October-to-date charges, led by RDS, EC2 compute, and the ALB. That
snapshot should be treated as an interim view rather than a final bill
or reliable forecast.

The most important outstanding technical item is to update the launch
template with the correct application security group before relying on
future Auto Scaling launches. The most important cost-control action is
to remove unneeded resources after the demonstration and verify the
account's billing view afterward.

------------------------------------------------------------------------

## Appendix A --- Key Paths and Commands

### Server paths

``` text
/opt/market-surveillance
/opt/market-surveillance/backend
/opt/market-surveillance/backend/venv
/opt/market-surveillance/frontend
/opt/market-surveillance/frontend/dist
/var/log/market-surveillance/backend.log
/etc/systemd/system/market-surveillance.service.d/override.conf
/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
```

### Useful commands

``` bash
# Check backend service
sudo systemctl status market-surveillance

# Restart backend service
sudo systemctl restart market-surveillance

# Check local API health
curl -i http://127.0.0.1:8000/api/health

# Build the frontend
cd /opt/market-surveillance/frontend
npm run build
```

### Example service drop-in

``` ini
[Service]
StandardOutput=append:/var/log/market-surveillance/backend.log
StandardError=append:/var/log/market-surveillance/backend.log
```

------------------------------------------------------------------------

## Appendix B --- Report Scope and Accuracy

This report is based on recorded deployment steps, console values, and
command outputs from the deployment conversation. It is not a live audit
of the AWS account. Resource states, charges, policies, and
configuration may have changed since the checks were performed. For
formal submission, add the project team's details, date of
demonstration, application screenshots, actual RDS configuration, and
any additional test results that are verified directly in AWS.
