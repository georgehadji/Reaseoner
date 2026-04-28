# Reasoner End-to-End Encryption (E2EE) Architecture

Reasoner v2.1 implements a comprehensive **Zero-Trust** security architecture. This ensures that data is never in plaintext while moving through the network or residing in storage.

## 1. Data In-Transit (Network Encryption)

### 1.1. External Traffic
All client-to-proxy traffic is protected by TLS 1.3/1.2 via the Caddy reverse proxy.
- **Automatic HTTPS:** Certificates are managed via Let's Encrypt.
- **HSTS:** `Strict-Transport-Security` is enforced with a 1-year max-age, including subdomains and preloading.
- **Secure Cookies:** All authentication and session cookies are flagged as `Secure`, `HttpOnly`, and `SameSite=Lax/Strict`.

### 1.2. Internal Network (Zero-Trust)
Traffic between containers within the Docker network is fully encrypted.
- **Internal PKI:** A `cert-generator` init-container generates a Root CA and leaf certificates for every service (`backend`, `frontend`, `postgres`, `redis`) on startup.
- **Service TLS:**
  - **PostgreSQL:** Strictly requires SSL/TLS for all connections.
  - **Redis:** Operates in TLS-only mode on port 6379; plaintext port is disabled.
  - **FastAPI (Backend):** Serves traffic via Gunicorn/Uvicorn with native TLS enabled.
  - **Next.js (Frontend):** Wraps the standalone server in a Node.js HTTPS proxy.
- **Upstream Verification:** Caddy uses HTTPS to communicate with backends, ensuring the internal network is opaque even to local attackers.

## 2. Data At-Rest (Application-Layer Encryption)

Reasoner protects sensitive information at the application layer before it reaches the database. This prevents data exposure if the database storage or backups are compromised.

### 2.1. Cryptographic Standards
- **Algorithm:** AES-256-GCM (via the Python `cryptography` library's Fernet implementation).
- **Mode:** Authenticated symmetric encryption.
- **Key Rotation:** Supported via `MultiFernet`, allowing a list of keys for seamless rotation.

### 2.2. Encrypted Data Fields
Encryption is applied transparently in the persistence layer:
- **API Keys:** Key names and permission scopes are encrypted in the SQLite `auth_store`.
- **Pipeline State:** Entire execution snapshots, including problem descriptions, thoughts, and final solutions, are encrypted in the PostgreSQL `snapshots` table.
- **Event Payloads:** All domain event data (PHASE_COMPLETED, etc.) is encrypted in the `events` table.
- **Read Models:** Denormalized CQRS read models are encrypted in the `read_models` table.

## 3. Key Management

Security relies on the protection of the `ENCRYPTION_KEY`.
- **Environment Variable:** Keys are provided via the `ENCRYPTION_KEY` environment variable.
- **Rotation:** To rotate keys, append the new key to the comma-separated list. The system will encrypt new data with the first key and decrypt old data using any key in the list.
- **Production Guard:** The system will refuse to start in `production` environment if a valid `ENCRYPTION_KEY` is not provided.

## 4. Security Verification
- **Network:** Inter-container traffic can be inspected via `tcpdump` inside the Docker network to confirm TLS encapsulation.
- **Database:** Querying the database directly via `psql` or `sqlite3` will show base64-encoded ciphertexts (starting with `gAAAAA...`) for all protected fields.
