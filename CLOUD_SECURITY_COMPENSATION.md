# Cloud Security Compensation Workflow

## Overview

This workflow demonstrates **automatic infrastructure teardown** when critical security vulnerabilities are detected during cloud provisioning. It's a real-world IT operations scenario showing how BPMN compensation events can protect your organization from deploying insecure infrastructure.

## Business Scenario

**DevOps Automation with Security-First Approach**

A DevOps team wants to provision cloud infrastructure (VPC, Storage, VM) but must ensure all deployed resources pass security validation. If critical vulnerabilities are discovered, the system automatically tears down ALL infrastructure to prevent security exposure.

### The Problem

Without automated compensation:
- ❌ Vulnerable VMs remain running in production
- ❌ Manual cleanup is error-prone and slow
- ❌ Security exposure window creates risk
- ❌ Forgotten resources create ongoing vulnerabilities

### The Solution

With BPMN compensation:
- ✅ Automatic teardown when vulnerabilities detected
- ✅ LIFO order ensures proper resource cleanup
- ✅ Zero human intervention required
- ✅ Complete audit trail of all actions
- ✅ No orphaned resources or security gaps

## Workflow Steps

### Provisioning Phase (Success Path)

```
START
  ↓
1. Create VPC (Virtual Private Cloud)
   ├─ Creates isolated network
   ├─ Generates VPC ID: vpc-xxxxx
   ├─ Creates Subnet: subnet-xxxxx
   └─ Registers compensation handler
  ↓
2. Create Storage Volume
   ├─ Creates encrypted block storage (100 GB)
   ├─ Generates Volume ID: vol-xxxxx
   ├─ Enables AES-256 encryption
   └─ Registers compensation handler
  ↓
3. Launch VM Instance
   ├─ Launches t3.medium instance
   ├─ Generates Instance ID: i-xxxxx
   ├─ Assigns public/private IPs
   ├─ Attaches storage volume
   ├─ Opens ports: 22, 80, 443
   └─ Registers compensation handler
  ↓
4. Run Security Scan
   ├─ Scans for CVEs
   ├─ Checks OS patches
   ├─ Analyzes security groups
   └─ Validates compliance
  ↓
✅ Security PASSED
  ↓
5. Register Infrastructure (CMDB)
  ↓
6. Send Success Notification
  ↓
END (Infrastructure Live)
```

### Security Failure Path (LIFO Teardown)

```
4. Run Security Scan
   ↓
   🔍 Scanning...
   ↓
   ❌ CRITICAL VULNERABILITIES DETECTED!
      • CVE-2024-12345: Remote Code Execution (9.8/10)
      • CVE-2024-67890: Privilege Escalation (8.1/10)
      • CVE-2024-11111: SSH Weak Cipher (5.3/10)
   ↓
Error Boundary Catches Exception
   ↓
Log Security Violation
   ↓
🔄 Emergency Teardown Event
   ↓
   Triggers compensation in LIFO order:
   ↓
   ┌────────────────────────────────────┐
   │ STEP 1: Terminate VM Instance      │
   │ (Most recent - destroy first)      │
   │ - Stop running instance            │
   │ - Detach storage volumes           │
   │ - Release public IP                │
   │ - Remove security groups           │
   │ - Wipe all data                    │
   └────────────────────────────────────┘
   ↓
   ┌────────────────────────────────────┐
   │ STEP 2: Delete Storage Volume      │
   │ (Second to destroy)                │
   │ - Create final snapshot (optional) │
   │ - Securely erase all data          │
   │ - Release storage quota            │
   └────────────────────────────────────┘
   ↓
   ┌────────────────────────────────────┐
   │ STEP 3: Delete VPC & Network       │
   │ (Oldest - destroy last)            │
   │ - Delete subnets                   │
   │ - Remove route tables              │
   │ - Delete internet gateway          │
   │ - Clean up all networking          │
   └────────────────────────────────────┘
   ↓
Send Security Alert Email
   ↓
END (All Infrastructure Destroyed)
```

## Files

### Workflow Definition
- **File**: `workflows/cloud-security-compensation-example.yaml`
- **Process**: Cloud Infrastructure Provisioning with Security Validation
- **Tasks**: 4 provisioning tasks + 3 compensation tasks
- **Lanes**: 2 (Provisioning & Security, Compensation)

### Test Contexts

#### Failure Context (Triggers Teardown)
**File**: `context-examples/cloud-security-failure-context.json`

```json
{
  "project_name": "WebApp-Production",
  "devops_team_email": "mkanoor@gmail.com",
  "cloud_region": "us-west-2",
  "vpc_cidr": "10.0.0.0/16",
  "storage_size_gb": 100,
  "storage_type": "gp3",
  "vm_instance_type": "t3.medium",
  "vm_image_id": "ami-ubuntu-22.04-outdated",
  "security_scan_should_fail": true  ← Triggers vulnerabilities
}
```

#### Success Context (No Teardown)
**File**: `context-examples/cloud-security-success-context.json`

```json
{
  "project_name": "WebApp-Production",
  "devops_team_email": "mkanoor@gmail.com",
  "cloud_region": "us-west-2",
  "vpc_cidr": "10.0.0.0/16",
  "storage_size_gb": 100,
  "storage_type": "gp3",
  "vm_instance_type": "t3.medium",
  "vm_image_id": "ami-ubuntu-22.04-hardened",
  "security_scan_should_fail": false  ← Passes security scan
}
```

### Test Script
- **File**: `test_cloud_security.py`
- **Usage**:
  ```bash
  python test_cloud_security.py failure   # Test security failure & teardown
  python test_cloud_security.py success   # Test successful provisioning
  ```

## Running the Test

### Test Security Failure Scenario (LIFO Teardown)

```bash
python test_cloud_security.py failure
```

**Expected Console Output:**

```
================================================================================
CLOUD SECURITY COMPENSATION TEST - INFRASTRUCTURE PROVISIONING
================================================================================
Scenario: FAILURE
================================================================================

☁️  Cloud Provisioning Details:
   Project: WebApp-Production
   Region: us-west-2
   VM Image: ami-ubuntu-22.04-outdated
   Storage: 100 GB gp3
   Security Scan Will: FAIL (vulnerabilities found)

🚀 Starting NEW workflow execution
🚀 Workflow Name: Cloud Infrastructure Provisioning with Security Validation

☁️  Step 1: Creating VPC (Virtual Private Cloud)...
   Project: WebApp-Production
   Region: us-west-2
   CIDR Block: 10.0.0.0/16
✅ VPC Created Successfully!
   VPC ID: vpc-xxxxxxxx
   Status: Available
   Subnets: Creating default subnet...
   Subnet ID: subnet-xxxxxxxx
📋 Registering compensation handler for task task_create_vpc: Delete VPC

💾 Step 2: Creating Block Storage Volume...
   VPC: vpc-xxxxxxxx
   Size: 100 GB
   Type: gp3
   Encryption: Enabled (AES-256)
✅ Storage Volume Created Successfully!
   Volume ID: vol-xxxxxxxx
   Size: 100 GB
   IOPS: 3000
   Status: Available
📋 Registering compensation handler for task task_create_storage: Delete Storage

🖥️  Step 3: Launching VM Instance...
   VPC: vpc-xxxxxxxx
   Subnet: subnet-xxxxxxxx
   Volume: vol-xxxxxxxx
   Instance Type: t3.medium
   Image: ami-ubuntu-22.04-outdated
✅ VM Instance Launched Successfully!
   Instance ID: i-xxxxxxxx
   Private IP: 10.0.1.XX
   Public IP: 54.XXX.XXX.XXX
   State: Running
   SSH: Port 22 (Open)
   HTTP: Port 80 (Open)
   HTTPS: Port 443 (Open)
📋 Registering compensation handler for task task_launch_vm: Terminate VM

🔒 Step 4: Running Security Vulnerability Scan...
   Target Instance: i-xxxxxxxx
   Public IP: 54.XXX.XXX.XXX
   Scanning ports: [22, 80, 443]

   🔍 Scanning for vulnerabilities...
   🔍 Checking OS patches...
   🔍 Scanning installed packages...
   🔍 Analyzing security groups...

❌ CRITICAL VULNERABILITIES DETECTED!

   🚨 CVE-2024-12345: Remote Code Execution (CRITICAL)
      Severity: 9.8/10 (CVSS)
      Package: openssl-1.0.2 (outdated)
      Impact: Allows remote attackers to execute arbitrary code
      Exploit: Publicly available

   🚨 CVE-2024-67890: Privilege Escalation (HIGH)
      Severity: 8.1/10 (CVSS)
      Package: sudo-1.8.21 (unpatched)
      Impact: Local user can gain root access

   ⚠️  CVE-2024-11111: SSH Weak Cipher (MEDIUM)
      Severity: 5.3/10 (CVSS)
      Service: SSH (Port 22)
      Impact: Man-in-the-middle attacks possible

   📊 SCAN SUMMARY:
      Critical: 1
      High: 1
      Medium: 1
      Total Issues: 3

   ❗ SECURITY POLICY VIOLATION!
   Infrastructure with CRITICAL vulnerabilities cannot be deployed.
   Initiating automatic teardown...

❌ Task Run Security Scan failed with error: Exception: SecurityScanFailure: Critical vulnerabilities detected
🎯 Error caught by boundary event: Security Scan Failed

🚨 ========================================
🚨 SECURITY POLICY VIOLATION DETECTED
🚨 ========================================
   Project: WebApp-Production
   Instance: i-xxxxxxxx
   Public IP: 54.XXX.XXX.XXX
   Violation: Critical vulnerabilities detected
   Action: Initiating EMERGENCY TEARDOWN
🚨 ========================================

🔄 ========================================
🔄 COMPENSATION TRIGGERED by: Emergency Teardown
🔄 Registered compensation handlers: ['task_create_vpc', 'task_create_storage', 'task_launch_vm']
🔄 ========================================

🔄 Triggering compensation for task task_launch_vm: Terminate VM
➡️  Following compensation flow to: ['Terminate VM Instance']

🔄 ========================================
🔄 COMPENSATION STEP 1 (of 3)
🔄 Terminating VM INSTANCE (most recent)
🔄 ========================================
   Instance ID: i-xxxxxxxx
   Public IP: 54.XXX.XXX.XXX
   State: Running → Shutting Down...
   ✅ Instance stopped
   ✅ Detaching storage volumes...
   ✅ Releasing public IP address
   ✅ Removing security group rules
   ✅ Instance terminated
   ✅ State: Terminated
   ✅ All instance data wiped
🔄 ========================================

🔄 Triggering compensation for task task_create_storage: Delete Storage
➡️  Following compensation flow to: ['Delete Storage Volume']

🔄 ========================================
🔄 COMPENSATION STEP 2 (of 3)
🔄 Deleting STORAGE VOLUME
🔄 ========================================
   Volume ID: vol-xxxxxxxx
   Size: 100 GB
   Status: Available → Deleting...
   ✅ Creating final snapshot (optional)...
   ✅ Securely erasing data...
   ✅ Volume deleted
   ✅ Storage quota released
   ✅ All data permanently destroyed
🔄 ========================================

🔄 Triggering compensation for task task_create_vpc: Delete VPC
➡️  Following compensation flow to: ['Delete VPC & Network']

🔄 ========================================
🔄 COMPENSATION STEP 3 (of 3)
🔄 Deleting VPC & NETWORK (oldest step)
🔄 ========================================
   VPC ID: vpc-xxxxxxxx
   Subnet ID: subnet-xxxxxxxx
   Status: Available → Deleting...
   ✅ Deleting subnet: subnet-xxxxxxxx
   ✅ Releasing route tables
   ✅ Removing network ACLs
   ✅ Deleting internet gateway
   ✅ VPC deleted: vpc-xxxxxxxx
   ✅ All networking resources cleaned up
🔄 ========================================

✅ EMERGENCY TEARDOWN COMPLETE - All 3 resources destroyed in LIFO order
   Infrastructure state: Fully cleaned up
   No vulnerable resources remain deployed

🔄 ======================================== (END COMPENSATION)

📧 Sending Security Alert Email...

================================================================================
✅ WORKFLOW COMPLETED SUCCESSFULLY
================================================================================

================================================================================
LIFO TEARDOWN ORDER VERIFICATION
================================================================================

Expected teardown order (LIFO - reverse of creation):

  FORWARD PROVISIONING ORDER:
    1. Create VPC           (task_create_vpc)
    2. Create Storage       (task_create_storage)
    3. Launch VM Instance   (task_launch_vm)
    4. Security Scan        (task_security_scan) ← FAILS HERE

  COMPENSATION ORDER (LIFO - REVERSE):
    1. Terminate VM         (comp_vm)          ← Last created, first destroyed
    2. Delete Storage       (comp_storage)     ← Second to destroy
    3. Delete VPC           (comp_vpc)         ← First created, last destroyed

🚨 Security Vulnerabilities Detected:
   • CVE-2024-12345: Remote Code Execution (CRITICAL)
   • CVE-2024-67890: Privilege Escalation (HIGH)
   • CVE-2024-11111: SSH Weak Cipher (MEDIUM)

📧 Check your email for detailed security alert!
   Email includes:
   - Complete vulnerability report
   - All resource IDs that were destroyed
   - Remediation steps

✅ ALL INFRASTRUCTURE CLEANED UP - No vulnerable resources remain

================================================================================
```

### Test Success Scenario

```bash
python test_cloud_security.py success
```

**Expected Outcome:**
- All 4 steps complete successfully
- Security scan passes (no vulnerabilities)
- Infrastructure registered and deployed
- Success confirmation email sent

## Email Notifications

### Security Alert Email (Failure)

```
Subject: 🚨 SECURITY ALERT - Infrastructure Teardown - WebApp-Production
To: mkanoor@gmail.com

🚨 SECURITY ALERT - CRITICAL VULNERABILITIES DETECTED 🚨

PROJECT: WebApp-Production
REGION: us-west-2
ACTION: EMERGENCY INFRASTRUCTURE TEARDOWN

SECURITY SCAN RESULTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ CRITICAL VULNERABILITIES DETECTED

🚨 CVE-2024-12345: Remote Code Execution (CRITICAL)
   Severity: 9.8/10 (CVSS)
   Package: openssl-1.0.2 (outdated)
   Impact: Allows remote attackers to execute arbitrary code
   Exploit: Publicly available

🚨 CVE-2024-67890: Privilege Escalation (HIGH)
   Severity: 8.1/10 (CVSS)
   Package: sudo-1.8.21 (unpatched)
   Impact: Local user can gain root access

⚠️  CVE-2024-11111: SSH Weak Cipher (MEDIUM)
   Severity: 5.3/10 (CVSS)
   Service: SSH (Port 22)
   Impact: Man-in-the-middle attacks possible

SUMMARY:
• Critical: 1
• High: 1
• Medium: 1
• Total Issues: 3

AUTOMATIC TEARDOWN COMPLETED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The following infrastructure was automatically torn down to prevent
security exposure:

🖥️  VM INSTANCE TERMINATED
   Instance ID: i-xxxxxxxx
   Public IP: 54.XXX.XXX.XXX
   Status: TERMINATED ✅
   Data: Wiped

💾 STORAGE VOLUME DELETED
   Volume ID: vol-xxxxxxxx
   Size: 100 GB
   Status: DELETED ✅
   Data: Securely erased

☁️  VPC DELETED
   VPC ID: vpc-xxxxxxxx
   Subnet ID: subnet-xxxxxxxx
   Status: DELETED ✅
   Network: Cleaned up

NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Update VM image to patch vulnerabilities
2. Use hardened base image with latest security updates
3. Re-run provisioning workflow with updated image
4. Ensure all packages are up-to-date

SECURITY POLICY:
Infrastructure with CRITICAL vulnerabilities cannot be deployed.
All resources have been automatically cleaned up to prevent exposure.

Security & Compliance Team
```

### Success Email

```
Subject: ✅ Cloud Infrastructure Provisioned - WebApp-Production
To: mkanoor@gmail.com

Your cloud infrastructure has been successfully provisioned and passed all security checks!

PROJECT: WebApp-Production
REGION: us-west-2

INFRASTRUCTURE DETAILS:

☁️  VPC (VIRTUAL PRIVATE CLOUD)
   VPC ID: vpc-xxxxxxxx
   Subnet ID: subnet-xxxxxxxx
   CIDR Block: 10.0.0.0/16
   Status: available

💾 STORAGE VOLUME
   Volume ID: vol-xxxxxxxx
   Size: 100 GB
   Type: gp3
   Encryption: AES-256
   Status: available

🖥️  VM INSTANCE
   Instance ID: i-xxxxxxxx
   Instance Type: t3.medium
   Private IP: 10.0.1.XX
   Public IP: 54.XXX.XXX.XXX
   State: running
   Image: ami-ubuntu-22.04-hardened

🔒 SECURITY VALIDATION
   Scan Status: PASSED ✅
   Vulnerabilities: None
   Compliance: Compliant

ACCESS INFORMATION:
SSH: ssh admin@54.XXX.XXX.XXX
HTTP: http://54.XXX.XXX.XXX
HTTPS: https://54.XXX.XXX.XXX

Your infrastructure is now live and ready for deployment!

Cloud Automation Team
```

## Why LIFO Order Matters for Cloud Resources

### Dependency Chain

```
VPC (Network Foundation)
  └─ requires deletion of: Storage Volume
      └─ requires deletion of: VM Instance (MUST be deleted first)
```

### Wrong Order (Would Fail)

```
❌ Delete VPC first
   → Error: VPC has attached instances
   → Manual intervention required
   → Partial cleanup, security exposure continues

❌ Delete Storage first
   → Error: Volume attached to running instance
   → VM still running with vulnerabilities
   → Security exposure continues
```

### Correct LIFO Order (Automatic Success)

```
✅ Delete VM first (most recent)
   → Detaches from storage
   → Releases network interfaces
   → Shuts down cleanly

✅ Delete Storage second
   → No longer attached to VM
   → Can delete cleanly

✅ Delete VPC last (oldest)
   → No resources remain
   → Clean deletion
```

## Real-World Use Cases

### 1. **Security Compliance Automation**
- Automatically tear down non-compliant infrastructure
- Prevent deployment of vulnerable resources
- Maintain security posture without manual intervention

### 2. **Cost Control**
- Prevent deployment of expensive resources with security issues
- Automatic cleanup saves cloud costs
- No orphaned resources billing you

### 3. **Infrastructure-as-Code Validation**
- Validate infrastructure before production deployment
- Catch misconfigurations early
- Rollback failed deployments automatically

### 4. **Multi-Cloud Provisioning**
- Works across AWS, Azure, GCP
- Standardized teardown process
- Consistent security enforcement

### 5. **DevOps Best Practices**
- Shift-left security (validate early)
- Automated remediation
- Complete audit trail for compliance

## Customization

### Change Security Scan Criteria

Modify the security scan script to check for different issues:

```python
# Check for specific CVEs
if "CVE-2024-99999" in scan_results:
    raise Exception("SecurityScanFailure: Specific CVE detected")

# Check compliance frameworks
if not compliance_check("PCI-DSS"):
    raise Exception("SecurityScanFailure: PCI-DSS non-compliant")

# Check configuration
if open_ports_include_insecure():
    raise Exception("SecurityScanFailure: Insecure ports exposed")
```

### Add More Resources

To add more cloud resources (e.g., Load Balancer, Database):

1. Add provisioning task after VM launch
2. Add compensation boundary
3. Add compensation task in lane 2
4. Connect flows

LIFO order will automatically handle the new resource.

### Integration with Real Cloud APIs

Replace script tasks with actual API calls:

```python
# Real AWS VPC creation
import boto3
ec2 = boto3.client('ec2', region_name=cloud_region)
vpc = ec2.create_vpc(CidrBlock=vpc_cidr)
vpc_id = vpc['Vpc']['VpcId']
```

## Key Takeaways

1. **Security First**: Vulnerable infrastructure is automatically destroyed
2. **LIFO Guarantee**: Resources torn down in reverse order (VM → Storage → VPC)
3. **Zero Manual Intervention**: Fully automated teardown
4. **Complete Audit Trail**: Every action logged and reported
5. **Real-World IT Scenario**: Demonstrates practical DevOps automation
6. **Compliance**: Enforces security policies automatically

This workflow shows how BPMN compensation events can protect your organization by ensuring that insecure infrastructure never remains deployed, even for a second.
