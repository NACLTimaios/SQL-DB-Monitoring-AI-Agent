# User Creation Guide - Troubleshooting White Screen

## Problem: White Screen When Creating Users

When trying to create a user in the Admin Settings page, you get a white screen and the user is not created.

## Root Cause

The most common reason is **password validation failure**. The password must meet strict security requirements:

### Password Requirements (MANDATORY)
✅ **12+ characters minimum**
✅ **At least one UPPERCASE letter** (A-Z)
✅ **At least one lowercase letter** (a-z)
✅ **At least one digit** (0-9)
✅ **At least one special character** (!@#$%^&*()_+-=[]{}...etc)

### Example Passwords That FAIL ❌
- `password123` — no uppercase, no special char
- `Password123` — no special char
- `Pass!` — too short (only 5 chars)
- `TestPassword` — no digit, no special char

### Example Passwords That WORK ✅
- `TestPassword123!`
- `NewUser@2026#Secure`
- `Admin_Pass123!Secure`
- `Welcome2024@NewUser`

## How to Fix the White Screen

### Step 1: Clear Browser Cache
1. Open browser developer tools (F12 or Ctrl+Shift+I)
2. Go to the **Application** tab
3. Click **Clear site data** or use **Ctrl+Shift+Delete**
4. Hard refresh the page: **Ctrl+F5** (or Cmd+Shift+R on Mac)

### Step 2: Check Password Requirements
The form now displays password requirements. Ensure your password meets ALL requirements:
```
🔒 Password must contain: 12+ chars, uppercase, lowercase, digit, special char (!@#$%^&* etc)
```

### Step 3: Create User with Valid Password
1. Enter a username (3+ chars, alphanumeric + underscore/hyphen only)
2. Enter a password that meets ALL requirements above
3. Select a role (Dashboard or Admin)
4. Click "Create User"

### Step 4: Check for Error Messages
If creation fails, you'll now see a clear error message explaining what went wrong:
- **"Password requirement: ..."** — Password doesn't meet security requirements
- **"Username requirement: ..."** — Username is invalid
- **"Username already taken: ..."** — That username already exists

## What Was Fixed

### Frontend Improvements (June 17, 2026)
✅ **Password requirements hint** — Now visible on the form
✅ **Better error messages** — Explains exactly what went wrong
✅ **Error boundary** — Prevents white screens from unhandled errors
✅ **Console logging** — Error details are logged for debugging

### Backend Features (Already Working)
✅ **Password strength validation** — Enforced via Palo Alto-grade requirements
✅ **Username validation** — Prevents invalid usernames
✅ **Duplicate prevention** — Can't create two users with same username
✅ **Role assignment** — Users can be created with Dashboard or Admin roles

## Testing User Creation

### Quick Test
1. Go to Admin Settings → User Management
2. Click "Create User" tab
3. Use this test user:
   - **Username:** `testuser`
   - **Password:** `TestPassword123!`
   - **Role:** Dashboard
4. Click "Create User"
5. Should see success message and auto-redirect to Users list

### Expected Success Message
```
✓ User 'testuser' created successfully
```

The page will automatically switch to the Users tab after 1.5 seconds, showing the new user in the list.

## Debugging Tips

If you still see issues:

1. **Open Developer Console** (F12)
   - Go to **Console** tab
   - Look for any error messages in red
   - Share these errors for debugging

2. **Check Network Tab** (F12)
   - Go to **Network** tab
   - Click "Create User"
   - Look for the `/api/users` POST request
   - Check the Response tab for error details

3. **Check API Health**
   - Open new tab and go to: `http://localhost:8084/api/health`
   - Should show: `{"status":"ok"...}`
   - If error, backend may not be running

## Username Rules

✅ **Valid Usernames:**
- `john_doe` — Alphanumeric + underscore ✓
- `test-user` — Alphanumeric + hyphen ✓
- `admin123` — Alphanumeric ✓

❌ **Invalid Usernames:**
- `jo` — Too short (min 3 chars)
- `john doe` — Contains space
- `john@example.com` — Contains @
- `user#1` — Contains invalid character (#)

## Password Strength Examples

Here are passwords that meet all requirements:

| Password | Reason |
|----------|--------|
| `SecurePass123!` | ✅ 14 chars, uppercase, lowercase, digit, special |
| `Admin@2026#Secure` | ✅ 17 chars, all requirements met |
| `TestPass_123456!` | ✅ 16 chars, all requirements met |
| `Welcome2NewUser!` | ✅ 15 chars, all requirements met |

## If You Forget Your Password

Currently, password reset is not implemented. To recover access:

1. Contact your system administrator
2. They can update your password via:
   ```bash
   curl -X PUT http://localhost:8084/api/users/{user_id} \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{"password":"NewPassword123!"}'
   ```

## Future Improvements

- [ ] Password strength meter on form
- [ ] Real-time validation feedback
- [ ] Password reset functionality
- [ ] Email notifications on account creation
- [ ] Two-factor authentication support

---

**Updated:** June 17, 2026
**Version:** 1.1
