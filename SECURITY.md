# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

We take the security of Jumbox seriously. If you believe you have found a security vulnerability in Jumbox, please report it responsibly:

- **Do NOT** open a public GitHub issue for sensitive security vulnerabilities.
- Please email the maintainers or open a private GitHub Security Advisory.
- Include a detailed description of the issue, steps to reproduce, and potential impact.

## Local-First Threat Model & Best Practices

Jumbox is designed as a **local-first transfer system** intended primarily for trusted local networks (Wi-Fi/LAN) or privately routed connections.

- **Public Internet Exposure:** If exposing Jumbox to the public internet, always place it behind a hardened reverse proxy with HTTPS/TLS encryption and appropriate firewall rules.
- **Single-Use Transfers:** Use the **Burn-After-Download** mode for confidential files to ensure they are immediately purged from host disk storage after recipient download.
