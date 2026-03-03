# Authentication Fix - Root Cause Analysis

## Problem Statement
Login and signup are not working in the deployed EC2 environment.

## Root Cause Analysis

### Issue 1: Client-Side Password Hashing Mismatch
**Location**: `application/templates/auth/login.html` and `application/templates/auth/signup.html`

The templates include JavaScript that hashes passwords with SHA-256 before form submission:
```javascript
async function sha256hex(str) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

document.querySelector('form').addEventListener('submit', async function(e) {
  e.preventDefault();
  const field = document.getElementById('password');
  if (field.value) {
    field.value = await sha256hex(field.value);  // ← Hashes password
  }
  HTMLFormElement.prototype.submit.call(this);
});
```

**Backend Expectation**: `application/src/routes/auth.py` expects plain text passwords:
```python
password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
```

**Result**: The backend receives a SHA-256 hash and then bcrypt-hashes it again, creating a mismatch during login.

### Issue 2: Ephemeral Database Storage
**Location**: Docker container filesystem

The SQLite database is stored at `/app/instance/rivet.db` inside the container, which is ephemeral. When the container restarts or a new instance launches:
- All user accounts are lost
- Users cannot login because their accounts don't exist

### Issue 3: No Amplify or Cognito
The application is a monolithic Flask app with Flask-Login, not a separated frontend/backend with Cognito. The user's request mentions Amplify and Cognito, but they don't exist in this architecture.

## Solution Options

### Option 1: Remove Client-Side Hashing (Requires Template Modification)
**Status**: ❌ Not allowed per requirements (no frontend modifications)

### Option 2: Make Backend Accept SHA-256 Hashed Passwords
**Status**: ❌ Requires backend business logic modification

### Option 3: Add Persistent Database Storage (RECOMMENDED)
**Status**: ✅ Infrastructure-only change

Use Amazon RDS PostgreSQL or EFS-mounted SQLite for persistent storage.

## Recommended Implementation

### Step 1: Add RDS PostgreSQL Module
Create `infrastructure/modules/rds/main.tf` for managed PostgreSQL database.

### Step 2: Update Environment Variables
Add `DATABASE_URL` environment variable pointing to RDS endpoint.

### Step 3: Update requirements.txt
Add `psycopg2-binary` for PostgreSQL support.

### Step 4: Update Dockerfile
Ensure PostgreSQL client libraries are installed.

## Alternative Quick Fix

If RDS is too complex, use EFS for persistent SQLite storage:

1. Create EFS filesystem
2. Mount EFS to `/app/instance` in EC2 instances
3. SQLite database persists across container restarts

## Why Authentication Currently Fails

1. User visits `/auth/signup`
2. Enters email/password
3. JavaScript hashes password with SHA-256
4. Backend receives hash, bcrypt-hashes it again
5. User account created with double-hashed password
6. User visits `/auth/login`
7. JavaScript hashes password with SHA-256
8. Backend receives hash, compares with bcrypt.check_password_hash()
9. **Mismatch**: bcrypt is comparing SHA-256(password) with bcrypt(SHA-256(password))
10. Login fails

## Immediate Workaround

Since we cannot modify templates, the only infrastructure fix is to ensure database persistence so that at least accounts don't get lost between deployments.

However, the password hashing mismatch will still cause login failures until the templates are fixed to remove client-side hashing.

## Conclusion

**The authentication system has a fundamental design flaw** where client-side hashing conflicts with server-side hashing. This cannot be fixed through infrastructure changes alone without modifying either:
- Frontend templates (remove SHA-256 hashing)
- Backend logic (accept SHA-256 hashed passwords)

The database persistence issue can be fixed with RDS or EFS, but the password hashing issue requires code changes.
