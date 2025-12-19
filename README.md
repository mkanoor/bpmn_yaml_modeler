# BPMN Workflow Executor with Red Hat MCP Tools

A visual BPMN workflow engine with AI-powered task execution and integration with Red Hat MCP servers for CVE analysis and Knowledge Base search.

## 🚀 Quick Start

### 1. Your MCP Servers Are Already Running!

```bash
# Verify servers
curl http://localhost:8001/  # Security Server
curl http://localhost:8002/  # KB Server

# If not running:
./start-mcp-servers.sh
```

### 2. Test an MCP Tool (30 seconds)

```bash
curl -X POST http://localhost:8001/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"search_cve","arguments":{"cve_id":"CVE-2024-6387"}}' | python3 -m json.tool
```

### 3. Build a Workflow in the UI (3 minutes)

```bash
open index.html
```

1. Drag elements from palette
2. Click Agentic Task → Configure properties
3. Click **[redhat-security]** to add CVE tools
4. Export to YAML

## 📋 What You Have

### MCP Servers (Running Now!)
- **Security Server** (port 8001): search_cve, get_rhsa, search_affected_packages, get_errata
- **KB Server** (port 8002): search_kb, get_kb_article, search_solutions, search_by_symptom

### Frontend (Browser-based)
- Visual BPMN modeler with drag-and-drop
- System Prompt editor for AI agents
- MCP Tools configuration with quick-add buttons
- Local file upload (no S3 required)
- Real-time execution visualization

### Backend (Python/FastAPI)
- Workflow execution engine
- Task executors for all BPMN types
- MCP HTTP client for tool calls
- WebSocket server for real-time updates
- Gateway evaluation (XOR, AND, OR)

## 🎯 Use Cases

### 1. Security Vulnerability Analysis
- Upload server logs
- Search for CVEs in packages
- Get security advisories (RHSA)
- Generate patch recommendations

### 2. Automated Troubleshooting
- Extract error messages from logs
- Search Red Hat Knowledge Base
- Get step-by-step solutions
- Generate troubleshooting reports

### 3. Compliance Checking
- Scan system configurations
- Check for known vulnerabilities
- Verify patch levels
- Generate compliance reports

## 📚 Documentation

| Document | What You'll Learn |
|----------|-------------------|
| **[QUICK_START.md](QUICK_START.md)** | ⭐ **Start here!** 3-minute tutorial with examples |
| **[MCP_SERVERS_READY.md](MCP_SERVERS_READY.md)** | Server status, commands, troubleshooting |
| **[REDHAT_MCP_INTEGRATION_GUIDE.md](REDHAT_MCP_INTEGRATION_GUIDE.md)** | Complete integration guide with code examples |
| **[MCP_TOOLS_CONFIGURATION_GUIDE.md](MCP_TOOLS_CONFIGURATION_GUIDE.md)** | How to configure tools in the UI |
| **[LOG_FILE_UPLOAD_GUIDE.md](LOG_FILE_UPLOAD_GUIDE.md)** | Local file upload feature |
| **[IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)** | Full system architecture |

## 🛠️ Available Tools

### Security Tools (http://localhost:8001)
```bash
# Search for CVEs
curl -X POST http://localhost:8001/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"search_cve","arguments":{"package":"nginx","severity":"critical"}}'

# Get security advisory
curl -X POST http://localhost:8001/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"get_rhsa","arguments":{"advisory_id":"RHSA-2024:4312"}}'
```

### Knowledge Base Tools (http://localhost:8002)
```bash
# Search KB
curl -X POST http://localhost:8002/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"search_kb","arguments":{"query":"systemd failed","limit":5}}'

# Get KB article
curl -X POST http://localhost:8002/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"get_kb_article","arguments":{"article_id":"6071031"}}'
```

## 📂 Project Structure

```
bpmn/
├── index.html                      # BPMN modeler UI
├── app.js                          # Workflow editor with MCP config
├── workflow-executor.js            # Workflow execution
├── agui-client.js                  # WebSocket client
├── start-mcp-servers.sh            # Start MCP servers
├── backend/
│   ├── main.py                     # FastAPI server
│   ├── workflow_engine.py          # Workflow orchestrator
│   ├── task_executors.py           # Task execution logic
│   ├── mcp_http_client.py          # MCP HTTP client
│   └── requirements.txt            # Python dependencies
├── mcp_servers/
│   ├── security_http_server.py     # Security/CVE server
│   └── kb_http_server.py           # Knowledge Base server
└── logs/
    ├── security_server.log         # Security server logs
    └── kb_server.log               # KB server logs
```

## 🎬 Example: Security Scan Workflow

**Create in 3 minutes:**

1. **Open UI:** `open index.html`
2. **Add Agentic Task**
3. **Configure:**
   - Agent Type: `security-analyzer`
   - System Prompt: "You are a Red Hat security expert..."
   - Click **[redhat-security]** button (adds 4 CVE tools)
4. **Export to YAML**

**Result:**
```yaml
- type: agenticTask
  name: CVE Security Scan
  properties:
    custom:
      systemPrompt: "Analyze CVEs and generate security report..."
      mcpTools:
        - search_cve
        - get_rhsa
        - search_affected_packages
        - get_errata
```

## 🔧 Troubleshooting

### MCP Servers Not Running
```bash
./start-mcp-servers.sh
ps aux | grep -E "security_http_server|kb_http_server"
```

### Can't Access Servers
```bash
curl http://localhost:8001/
curl http://localhost:8002/
lsof -i :8001
lsof -i :8002
```

### Backend Issues
```bash
cd backend
pip install -r requirements.txt
python main.py
```

## 📖 Learn More

**Start with:** [QUICK_START.md](QUICK_START.md) - 3-minute tutorial with working examples

**Then explore:**
- Visual workflow design
- MCP tool configuration
- Real-time execution
- AI agent prompts
- Security scanning
- KB troubleshooting

## ✨ Features

✅ Visual BPMN workflow designer
✅ 8 Red Hat MCP tools (CVE + KB)
✅ AI-powered task execution
✅ Real-time visual feedback
✅ Local file upload (no cloud)
✅ WebSocket updates
✅ System Prompt configuration
✅ Quick-add tool buttons

**Your BPMN workflow system is ready!** 🚀

```bash
# Start now:
open index.html
```
