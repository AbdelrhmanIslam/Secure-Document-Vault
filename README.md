# Secure Document Vault

**Secure Document Vault** is a comprehensive, production-ready Flask web application designed for securely uploading, storing, and verifying sensitive files. It employs advanced cryptographic techniques to encrypt files at rest, and uses cryptographic hashes and digital signatures to ensure end-to-end document integrity. 

This project goes beyond simple file storage by providing robust security measures including JSON Web Tokens (JWT), Role-Based Access Control (RBAC), Time-Based One-Time Passwords (TOTP) for mandatory Two-Factor Authentication (2FA), and OAuth 2.0 integration for seamless third-party logins.

---

## Key Features

### Authentication & Authorization
*   **Role-Based Access Control (RBAC):** Three distinct tiers of access (`Admin`, `Manager`, and `User`) ensure strict separation of duties.
*   **Mandatory Two-Factor Authentication (2FA):** All users, regardless of registration method, must complete TOTP-based 2FA setup to access the vault.
*   **OAuth 2.0 Integration:** Seamless login and registration using **GitHub** and **Google** accounts, automatically linked with 2FA protection.
*   **JWT & Secure Sessions:** JWT-based authentication stored in `HttpOnly`, `SameSite=Strict` cookies to prevent XSS.
*   **Password Security:** bcrypt password hashing with strict password complexity policies enforced upon registration.
*   **CSRF Protection:** All state-changing forms are rigorously protected with Cross-Site Request Forgery (CSRF) tokens using Flask-WTF. Verified across all UI templates.

### Document Security & Integrity
*   **Encryption at Rest:** Uploaded files are immediately encrypted on the server using symmetric encryption (Fernet/AES).
*   **Cryptographic Hashing:** A SHA-256 hash is generated for every document upon upload to provide a verifiable fingerprint.
*   **RSA Digital Signatures:** Documents are signed using asymmetric RSA keys. The application automatically generates a `private_key.pem` and `public_key.pem` upon first boot.
*   **Integrity Verification:** A dedicated verification workflow allows users and managers to cryptographically verify that a document has not been tampered with since upload by checking both the SHA-256 hash and the RSA signature.

### Administrative Tools
*   **Admin Dashboard:** Admins can manage user accounts, change user roles, enable/disable accounts, and securely delete users and their associated files.
*   **Review Queue:** Managers have access to a vault-wide review queue to inspect metadata, verify document integrity, and monitor uploads without necessarily downloading the files.

---

## Database Schema & Architecture

The application utilizes SQLAlchemy for ORM, managing a structured relational database (SQLite by default, but configurable for PostgreSQL/MySQL).

### 1. `User` Model
Handles authentication, access levels, and relationships to uploaded documents.
*   **id**: Integer, Primary Key.
*   **username**: String, User's display name.
*   **email**: String, Unique identifier for login.
*   **password_hash**: String, Bcrypt hashed password.
*   **role**: String (`Admin`, `Manager`, `User`).
*   **is_active**: Boolean, securely enable/disable user login and API access.
*   **twofa_secret**: String, Base32 secret for TOTP authenticator.
*   **twofa_enabled**: Boolean, marks if the user has verified their 2FA setup.
*   **oauth_provider** & **oauth_id**: Strings for GitHub/Google SSO tracking.
*   **documents**: One-to-Many relationship linked to the `Document` model.

### 2. `Document` Model
Tracks file metadata, encryption locations, and cryptographic integrity parameters.
*   **id**: Integer, Primary Key.
*   **filename**: String, Server-side unique encrypted filename.
*   **original_filename**: String, User-facing filename.
*   **file_size**: Integer, in bytes.
*   **mime_type**: String, e.g., application/pdf.
*   **status**: String (`Pending`, `Approved`, `Rejected`).
*   **uploader_id**: Integer, Foreign Key linked to `User`.
*   **reviewed_by_id**: Integer, Foreign Key linked to the reviewing `Manager` or `Admin`.
*   **encrypted_path**: String, Path on the local filesystem or cloud storage.
*   **file_hash**: String, SHA-256 cryptographic hash of the original file content.
*   **signature**: Text, Asymmetric RSA digital signature verifying the file_hash.

---

## Detailed Project Structure

```text
data-integrity/
│
├── app.py                  # Application factory, global routing, error handlers & CSRF init.
├── config.py               # Core configuration class, environment variable parsers.
├── models.py               # SQLAlchemy ORM definitions for User and Document tables.
├── extensions.py           # Instantiations of Flask extensions (db, migrate, csrf).
├── cli.py                  # Custom CLI commands (`flask create-admin`, `flask create-manager`).
│
├── auth/                   # Blueprint: Authentication & Users
│   ├── routes.py           # Endpoints: Login, register, 2FA workflows, OAuth callbacks.
│   ├── oauth.py            # Authlib integration for GitHub and Google SSO.
│   └── utils.py            # JWT token encoding/decoding and authorization helpers.
│
├── documents/              # Blueprint: Core Application Logic
│   ├── routes.py           # Endpoints: Dashboard, Admin Panel, Upload, Download, Review.
│   └── crypto_utils.py     # Cryptographic core: Fernet encryption, RSA signing/verification.
│
├── templates/              # Jinja2 HTML View Layer
│   ├── base.html           # Main application layout.
│   ├── admin.html          # Admin management portal.
│   ├── dashboard.html      # User's personal document vault.
│   ├── manager_dashboard.html # Manager's review queue.
│   ├── upload.html         # Secure upload form.
│   └── ... (Auth & 2FA templates)
│
├── static/                 # Static Assets
│   └── style.css           # Modern, responsive, utility-based glassmorphism styling.
│
├── migrations/             # Alembic database migration revisions.
└── requirements.txt        # Python package dependencies.
```

---

## Default Roles & Permissions

| Feature | `Admin` | `Manager` | `User` |
| :--- | :--- | :--- | :--- |
| **Upload Documents** | Yes | Yes (Own only) | Yes (Own only) |
| **Download Documents** | Yes (All) | Yes (Own only) | Yes (Own only) |
| **Delete Documents** | Yes (All) | Yes (Own only) | Yes (Own only) |
| **Verify Document Integrity**| Yes (All) | Yes (All in Review Queue) | Yes (Own only) |
| **View Review Queue** | Yes | Yes | No |
| **View All Users** | Yes | No | No |
| **Change User Roles** | Yes | No | No |
| **Disable/Delete Users** | Yes | No | No |

---

## Installation & Setup Steps

### 1. Clone & Prepare the Environment
Ensure you have Python 3.9+ installed.

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the required dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory.

```env
# Application Secrets
SECRET_KEY=your-super-secret-flask-key
JWT_SECRET_KEY=your-jwt-secret-key

# Database and Storage
DATABASE_URL=sqlite:///database.db
UPLOAD_FOLDER=uploads

# Document Encryption Key (Must be a valid Fernet key)
# Generate one using: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-fernet-key

# File Upload Constraints
MAX_CONTENT_LENGTH=16777216  # 16 MB max upload size
UPLOAD_EXTENSIONS=txt,pdf,png,jpg,jpeg

# Cookie & Session Security
JWT_COOKIE_NAME=token
JWT_COOKIE_MAX_AGE=3600
JWT_COOKIE_SAMESITE=Strict
SESSION_COOKIE_SAMESITE=Lax
SESSION_LIFETIME_MINUTES=15
WTF_CSRF_TIME_LIMIT=3600

# OAuth 2.0 Credentials (Optional, but required for Google/GitHub login)
OAUTH_GITHUB_CLIENT_ID=your_github_client_id
OAUTH_GITHUB_CLIENT_SECRET=your_github_client_secret
OAUTH_GOOGLE_CLIENT_ID=your_google_client_id
OAUTH_GOOGLE_CLIENT_SECRET=your_google_client_secret

# Development only: Allow OAuth over HTTP
AUTHLIB_INSECURE_TRANSPORT=1
```

### 3. Database Initialization
Initialize the database and create the initial Admin account.

```bash
# Run database migrations to create the tables
flask --app app:create_app db upgrade

# Create the default admin account
flask --app app:create_app create-admin
```

*(Note: If you are upgrading from an older legacy database without Alembic migrations, run `flask --app app:create_app db stamp 20260510_01` before running `db upgrade`.)*

### 4. Run the Application
Start the Flask development server:

```bash
python app.py
```
*(The server will start securely on `https://127.0.0.1:5000` if `cert.pem` and `key.pem` are present)*

---

## OAuth 2.0 Configuration Guide

To enable "Continue with GitHub" and "Continue with Google", create developer applications in both platforms and populate the `OAUTH_*` variables in your `.env` file.

**Important Callback URLs:**
*   **GitHub Callback URL:** `https://127.0.0.1:5000/auth/github/callback`
*   **Google Callback URL:** `https://127.0.0.1:5000/auth/google/callback`

*(If you run the application on `localhost` instead of `127.0.0.1`, ensure your provider configuration matches exactly).*

---

## Security Audit & CSRF Protection Review

*   **CSRF Implementation is Active and Correct:** 
    *   The project enforces global Cross-Site Request Forgery (CSRF) protection via `Flask-WTF`.
    *   `csrf.init_app(app)` is configured correctly in `app.py`.
    *   **Audit Complete:** Every single state-changing POST route, including Dashboard Deletions, Manager Status Updates, Admin Role Assignments, File Uploads, 2FA Setup/Verification, and User Authentication (Login/Register) is protected.
    *   All HTML forms correctly implement `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
*   **HTTPS:** The application is now configured to run securely via HTTPS out-of-the-box when `cert.pem` and `key.pem` SSL certificates are provided in the root directory. In a production environment, proper SSL certificates should be used, and the `AUTHLIB_INSECURE_TRANSPORT` flag should be removed. Session and JWT cookies are strictly configured to only transmit over secure connections.
*   **RSA Keys:** If `private_key.pem` and `public_key.pem` are not found in the root directory, the application generates them automatically. In production, these should be securely backed up and stored.
*   **Disabled Accounts:** Changing a user's status to inactive immediately invalidates their session and prevents all future logins.