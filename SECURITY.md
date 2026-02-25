# Security Best Practices

## Protected Files

The following files are **NOT tracked** in git to protect sensitive information:

### Configuration Files
- `config.yaml` - Contains IPs, credentials, and environment-specific settings
- **Always use**: `config.yaml.example` as your template

### SSH Keys
- `*.pem` - Private key files
- `*.key` - SSH private keys
- `.ssh/` - SSH directory

### Results & Logs
- `Results/` - Test results may contain network topology information
- `logs/` - Log files may contain sensitive debugging information

## Setup for New Users

```bash
# 1. Clone repository
git clone https://github.com/yourusername/netperf-orchestrator.git
cd netperf-orchestrator

# 2. Create your config from template
cp config.yaml.example config.yaml

# 3. Edit with your environment details
nano config.yaml

# 4. Your config.yaml is automatically ignored by git
```

## What's Safe to Share

✅ **Safe to commit:**
- `config.yaml.example` - Template with placeholder values
- `*.py` - Python source code
- `README.md` - Documentation
- `requirements.txt` - Dependencies

❌ **Never commit:**
- `config.yaml` - Your actual configuration
- SSH private keys
- Passwords or credentials
- Internal IP addresses
- Company-specific information

## Sanitizing for Public Release

If you need to share configuration examples:

1. Replace real IPs with placeholders:
   - `10.241.0.118` → `<PACKETSTORM_IP>`
   - `96.37.176.19` → `<CLIENT_IP>`

2. Replace credentials:
   - Real passwords → `<password>`
   - Usernames → `<username>`

3. Replace company domains:
   - `ctec-jump.ctec.charterlab.com` → `<jumpserver>`

## Current Protection Status

✅ `config.yaml` is in `.gitignore`
✅ `config.yaml` removed from git history (latest commit)
✅ Local `config.yaml` preserved and functional
✅ `config.yaml.example` available as template

## Verification

Check if config.yaml is ignored:
```bash
git status
# Should NOT show config.yaml as modified
```

Check if local config exists:
```bash
ls -la config.yaml
# Should show the file exists
```

---

**Remember**: Never commit sensitive information to public repositories!
