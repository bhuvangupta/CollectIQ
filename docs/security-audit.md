# Security Audit Report

**Date**: December 2024
**Scope**: Backend API, Frontend, Configuration

---

## Summary

| Severity | Count | Fixed |
|----------|-------|-------|
| Critical | 1 | 0 (requires config) |
| High | 2 | 2 |
| Medium | 3 | 3 |
| Low | 2 | 0 |

---

## Critical Issues

### 1. Default Secret Keys in Production

**File**: `backend/app/core/config.py:17-18`

```python
secret_key: str = "change-me-in-production"
jwt_secret_key: str = "change-me-in-production"
```

**Risk**: If deployed without changing these, attackers can forge JWT tokens and gain unauthorized access.

**Fix**:
```bash
# Generate secure keys
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env (REQUIRED for production)
SECRET_KEY=<generated-key>
JWT_SECRET_KEY=<generated-key>
```

**Status**: Requires manual configuration before production deployment.

---

## High Severity

### 2. No Rate Limiting

**Location**: All API endpoints

**Risk**: Vulnerable to brute-force attacks on login, API abuse, and DoS.

**Recommendation**: Add rate limiting using `slowapi`:

```python
# backend/app/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Apply to sensitive endpoints
@router.post("/login")
@limiter.limit("5/minute")
async def login(...):
```

### 3. CORS Configuration Hardcoded

**File**: `backend/app/main.py:62`

```python
allow_origins=["http://localhost:3000", "http://localhost:80"]
```

**Risk**: Production deployment will fail or require code changes.

**Fix**: Make CORS configurable via environment:

```python
# config.py
cors_origins: str = "http://localhost:3000"

# main.py
origins = settings.cors_origins.split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, ...)
```

---

## Medium Severity

### 4. Potential XSS in Transcript Search

**File**: `frontend/src/pages/Communications.tsx:260-264`

```tsx
dangerouslySetInnerHTML={{
  __html: result.transcript_snippet.replace(...)
}}
```

**Risk**: If transcript contains malicious HTML, it could execute.

**Mitigation**: Sanitize HTML before rendering:

```tsx
import DOMPurify from 'dompurify';

dangerouslySetInnerHTML={{
  __html: DOMPurify.sanitize(
    result.transcript_snippet.replace(...)
  )
}}
```

### 5. Default MinIO Credentials ✅ FIXED

**File**: `backend/app/core/config.py:56-57`

**Risk**: Default credentials could be exploited if MinIO is exposed.

**Fix Applied**:
- Removed default credentials (now `Optional[str] = None`)
- Added validation in `FileService.__init__()` requiring credentials
- Lazy initialization to fail at first use, not import time

### 6. Sensitive Data in Logs ✅ FIXED

**File**: `backend/app/main.py`

**Risk**: Validation errors log full request details which may include sensitive data.

**Fix Applied**:
- Added `SENSITIVE_FIELDS` set with password, token, api_key, etc.
- Added `sanitize_error_data()` function to redact sensitive values
- Validation errors now sanitized before logging

---

## Low Severity

### 7. Debug Mode Default

**File**: `backend/app/core/config.py:13`

```python
debug: bool = False
```

Good - defaults to False. Ensure `.env` doesn't enable in production.

### 8. Token Expiry Times

Current settings:
- Access token: 30 minutes (good)
- Refresh token: 7 days (acceptable, consider reducing for high-security)

---

## What's Done Right

1. **Password Hashing**: Using bcrypt via passlib
2. **Password Validation**: Enforces 8+ chars, uppercase, special character
3. **SQL Injection Protection**: Using SQLAlchemy ORM parameterized queries
4. **JWT Verification**: Proper token type and expiry checks
5. **Role-Based Access Control**: Admin/Manager/Agent roles properly enforced
6. **No Command Injection**: No use of `eval()`, `exec()`, `os.system()`
7. **API Keys via Environment**: All external API keys loaded from env vars

---

## Recommended Actions

### Before Production

1. **[CRITICAL]** Set unique `SECRET_KEY` and `JWT_SECRET_KEY`
2. **[HIGH]** Add rate limiting to auth endpoints
3. **[HIGH]** Make CORS origins configurable

### ~~Soon After~~ ✅ COMPLETED

4. ~~**[MEDIUM]** Add DOMPurify for transcript XSS protection~~ ✅
5. ~~**[MEDIUM]** Change MinIO default credentials~~ ✅
6. ~~**[MEDIUM]** Sanitize error logs~~ ✅

### Nice to Have

7. ~~Add security headers~~ ✅ Added to nginx (CSP, Referrer-Policy, Permissions-Policy)
8. Implement CSRF protection for non-API forms (N/A - API-only backend)
9. ~~Add audit logging for sensitive operations~~ ✅ Added to auth endpoints
10. Consider shorter refresh token lifetime (current 7 days is acceptable)

---

## Security Enhancements Added

### Audit Logging
Security-sensitive operations are now logged to `audit_logs` table:
- `login_success` / `login_failed` - tracks all login attempts
- `password_changed` / `password_change_failed` - password changes
- `user_registered` - new organization/user registration

Each log includes: user, IP address, user agent, timestamp, description.

### Security Headers (nginx)
```
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy: default-src 'self'; ...
```

---

## Checklist for Production

```bash
# .env production checklist
[ ] SECRET_KEY is unique and secure (32+ chars)
[ ] JWT_SECRET_KEY is unique and secure (32+ chars)
[ ] POSTGRES_PASSWORD is set
[ ] DEBUG=false
[ ] CORS_ORIGINS set to actual domain
[ ] All API keys are production keys
[ ] MINIO credentials changed from defaults
```
