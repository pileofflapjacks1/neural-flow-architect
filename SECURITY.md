# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x (foundation) | ✅ security fixes |
| unreleased main | ✅ best effort |

## Neural data is high-sensitivity

Treat any neural recordings, derived features that can identify a person, session
logs tied to identity, and implant-related metadata as **highly sensitive biometric data**.

### Never

- Commit real user neural data to git  
- Open public issues that attach raw or lightly processed neural files from people  
- Enable cloud processing of neural streams without explicit, granular consent  
- Log raw samples at info level in default configs  

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email (placeholder until maintainers publish a real address):

`security@neural-flow-architect.example`

Include:

1. Description of the issue  
2. Steps to reproduce  
3. Impact assessment (especially regarding neural data exfiltration)  
4. Any suggested fix  

We aim to acknowledge reports within 5 business days.

## Safe defaults we try to preserve

- `NFA_LOCAL_ONLY=true`  
- `NFA_ALLOW_CLOUD_LLM=false`  
- IoT integrations off until enabled  
- Dry-run mode for environment actions  
- Consent checks before persistence beyond ephemeral buffers  

If a PR weakens these defaults, it requires explicit maintainer review.
