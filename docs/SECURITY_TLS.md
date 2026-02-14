# TLS / HTTPS policy

By default `security.allow_insecure: false`.

When insecure is not allowed:
- `views.*` URLs must be `https://...`
- Home Assistant WebSocket must be `wss://...`
- Nightscout base URL must be `https://...`

To allow local HTTP during bring-up:

```yaml
security:
  allow_insecure: true
```

Do not ship a deployed configuration with insecure traffic if the kiosk is used for medical data.
