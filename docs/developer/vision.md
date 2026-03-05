Geldstrom Gateway: Comprehensive Architecture & Vision1. Vision and MissionMission: To abstract the highly complex, stateful German FinTS banking infrastructure into a modern, lightning-fast, stateless REST API, without ever compromising the strict security and privacy of the end-user.Vision: The Geldstrom Gateway acts as a "FinTS-as-a-Service" layer. It enables a "Managed Mode" for applications like SWEN, allowing developers to leverage a professional FinTS Product ID and an up-to-date bank directory out-of-the-box. By acting as a pure, zero-knowledge protocol translator, the Gateway empowers developers to build financial applications effortlessly while legally insulating them from storing sensitive banking credentials.2. Core PrinciplesThe architecture is strictly governed by the following foundational principles:Zero-Knowledge Persistence: The Gateway never stores banking PINs, credentials, or financial data on disk. Sensitive state is completely ephemeral.Domain-Driven Design (DDD): Strict separation of concerns within a monorepo. Pure FinTS protocol logic (geldstrom), stateless high-security routing (gateway), and business/database management (admin) are distinct bounded contexts.Network Isolation (The DMZ Pattern): The public-facing Gateway has absolutely no direct access to the primary relational database. It reads strictly from a highly restricted, temporary operational cache.Reactive Scalability: No HTTP connection is ever held open waiting for human interaction (like 2FA). The system uses request-response-disconnect paradigms to support infinite horizontal scaling.Open Provenance: Trust is established through cryptographic verification. Clients can independently verify the exact open-source commit running on the remote Gateway nodes.Minimalist Legal Logging: Persistent logs are restricted exclusively to the requester's IP address, timestamp, and API account ID for legal audit and abuse prevention.3. High-Level Architecture & Involved ServicesDeployment TopologyTo ensure the public-facing Gateway cannot compromise user data if breached, the system is divided into a Public Network (Data Plane) and a Private Network (Control Plane).Geldstrom Gateway (Public Data Plane): A stateless FastAPI application. It connects only to a shared Redis cluster and an internal gRPC interface. It parses TLS 1.3 requests, translates them to FinTS (or future protocols like PSD2), and drops credentials from memory.Geldstrom Admin Service (Private Control Plane): Connects to PostgreSQL. Manages users, billing, and the bank directory. It pushes active configurations to Redis and exposes a private, gRPC-based internal endpoint for the Gateway to verify keys during a cache miss.Operational Cache (Redis): Acts as the high-speed bridge between the Admin Service and the Gateway, storing active API key hashes and temporary 2FA session states.Primary Database (PostgreSQL): The ultimate source of truth, accessible only by the Admin Service.Component Diagramgraph TD
    subgraph "User Environment"
        UI[SWEN Frontend]
        BE[SWEN Backend]
    end

    subgraph "Geldstrom Monorepo (Deployed as Separate Containers)"
        direction TB

        subgraph "Public Facing (DMZ)"
            GW[Gateway Service]
            Lib[Geldstrom FinTS Domain]
            GW -- "imports" --> Lib
        end

        subgraph "Internal Private Network"
            Cache[(Redis - Active Keys & Sessions)]
            Admin[Admin Interface Service]
            DB[(PostgreSQL - Users/Billing)]
        end

        GW -- "1. Read / Validate" --> Cache
        GW -- "2. Cache Miss Fallback (gRPC)" --> Admin
        Admin -- "Push Updates" --> Cache
        Admin -- "Source of Truth" --> DB
    end

    subgraph "Banking Network"
        Bank[Bank FinTS Server]
    end

    UI <--> BE
    BE -- "TLS 1.3 Request (Protocol + BLZ + Date Range + PIN)" --> GW
    GW -- "Protocol Fetch (URL + ProdID + PIN)" --> Bank

4. Technical Design & System Architecture4.1. Monorepo Structure (Source Layout)geldstrom-repo/
├── src/
│   ├── geldstrom/      # Protocol Package (Pure Domain/Infra for FinTS)
│   ├── gateway/        # Stateless API Layer (FastAPI)
│   │   ├── domain/      # Gateway Domain Models (Redis Session State, Ephemeral Keys)
│   │   ├── application/
│   │   └── api/
│   └── admin/          # Control Plane & Admin Tools (FastAPI)
│       ├── domain/      # DDD Bounded Contexts (Users, Keys, Institutes)
│       ├── application/ # Use Cases (RotateKey, DB Migrations)
│       └── infrastructure/
│           └── persistence/ # SQLAlchemy + PostgreSQL
├── proto/              # Protobuf definitions for internal gRPC contracts
├── .github/workflows/  # Transparent CI/CD build pipelines
├── tests/
└── pyproject.toml

4.2. Database Layout, Persistence & LoggingThe system utilizes two distinct data stores to balance security, speed, and persistence:PostgreSQL (System of Record): Stores Users, Hashed API Keys (Argon2), the Bank BLZ Directory, and Billing Status. Only the Admin Service can read/write here.Redis (Operational Data Store): Stores transient data. It holds currently active API Key hashes (pushed by the Admin service) and temporary, encrypted FinTS session blobs for 2FA handling.Audit Logging: The Gateway asynchronously ships minimal legal logs (timestamp, api_key_hash, remote_ip, request_type, protocol) to a secure bucket or logging pipeline, physically separated from business data.4.3. Gateway Domain Model (Redis State)While the Admin Service owns the persistent PostgreSQL domain, the Gateway maintains its own localized Domain Model specifically for interacting with Redis. This ensures strict type safety and validation for transient data:Session State Models: Strongly typed entities representing the parked dialogue state, ensuring the encrypted JSON blob is perfectly serialized and deserialized when pausing/resuming a 2FA challenge.Cached Auth Models: Lightweight domain objects representing the cached API key validation responses received from the Admin Service, preventing malformed data from causing authorization bypasses.4.4. Ephemeral Credential Handling (Security Model)Because FinTS requires plain-text PINs to construct signed message segments (e.g., HKIDN), the Gateway must hold the PIN temporarily:Transport Security: Strict enforcement of TLS 1.3 from SWEN to the Gateway.Volatile Memory: The Gateway parses the request, executes the geldstrom client, and relies on Python's garbage collection to clear the PIN from RAM immediately after the payload is signed.Log Scrubbing: Middleware explicitly intercepts and scrubs request bodies and outgoing traces, ensuring credentials never touch stdout, APM tools (like Sentry), or error logs.4.5. Reactive Asynchronicity & Decoupled 2FA LifecycleHolding HTTP connections open while users hunt for a TAN destroys server scalability. The Gateway uses a decoupled, non-blocking flow:Initial Request: SWEN asks the Gateway for transactions.Bank Challenge: The bank returns a 2FA challenge. The Gateway serializes the active protocol client state (e.g., Dialog ID, Message Number) into an encrypted JSON blob based on its Session State domain model.Session Parking: The blob is saved to Redis with a strict 5-minute TTL.Immediate Disconnect: The Gateway returns 200 OK with status: "CHALLENGE_REQUIRED" and a session_id, instantly closing the HTTP connection and freeing the API worker.Resume Request: SWEN sends a new request with the session_id and tan_response. The Gateway rehydrates the state from Redis, completes the handshake, and returns the transactions.4.6. Stateless Data RetrievalThe Gateway does not track what data a user has already synced.Clients must provide explicit start_date and end_date parameters.The Gateway acts as a pure conduit, returning raw transaction data. Deduplication is the responsibility of the SWEN application.4.7. System Resilience & gRPC FallbackIf the Redis container crashes and loses its in-memory data, the Gateway utilizes a Cache-Aside Fallback to self-heal without exposing PostgreSQL:Gateway checks Redis for SHA256(API_KEY).On Cache Miss: Gateway executes a high-speed gRPC call to the Admin Service: Admin.ValidateKey(KeyRequest).The Admin Service securely queries Postgres and returns the KeyResponse.The Gateway serves the request and asynchronously repopulates Redis with the result, restoring maximum throughput.gRPC is used here for its binary Protobuf performance, HTTP/2 multiplexing, and strict type-safety contracts.4.8. Transparency & ProvenanceThe Gateway image is built transparently using public GitHub Actions workflows.The API exposes a /v1/system/version endpoint revealing the active git_commit_hash and docker_image_sha256, allowing clients to cryptographically verify the running container matches the open-source repository.5. API Blueprint (Gateway)EndpointsGET /v1/system/version: Returns public provenance data.POST /v1/transactions/fetch: Fetches transactions statelessly or resumes a parked 2FA session.Gateway API Contract (OpenAPI 3.0)openapi: 3.0.3
info:
  title: Geldstrom Gateway API
  description: A stateless, zero-knowledge gateway for the German FinTS banking protocol, built with future multi-protocol support (e.g. PSD2).
  version: 1.0.0
servers:
  - url: [https://api.geldstrom.io](https://api.geldstrom.io)
security:
  - ApiKeyAuth: []

paths:
  /v1/system/version:
    get:
      summary: Get system version and provenance
      security: []
      responses:
        '200':
          description: System version details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SystemVersion'

  /v1/transactions/fetch:
    post:
      summary: Fetch transactions statelessly
      description: Connects to the requested bank via the specified protocol (e.g., FinTS), authenticates ephemerally, and returns parsed transactions for a specific date range.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/FetchTransactionsRequest'
            example:
              connection:
                protocol: "fints"
                bank_code: "12345678"
                username: "user_123"
                pin: "secret_pin"
              iban: "DE1234..."
              date_range:
                from: "2023-10-01"
                to: "2023-10-31"
      responses:
        '200':
          description: Successful transaction fetch
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TransactionResponse'
        '401':
          description: Unauthorized (Invalid API Key or Invalid Bank Credentials)
        '422':
          description: Validation Error
        '502':
          description: Bad Gateway (Bank Server Error)

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

  schemas:
    SystemVersion:
      type: object
      properties:
        version: { type: string }
        git_commit_hash: { type: string }
        docker_image_sha256: { type: string }

    BankConnection:
      type: object
      required: [protocol, bank_code, username, pin]
      properties:
        protocol:
          type: string
          description: "The banking protocol to use for the connection (e.g., 'fints', 'psd2'). Currently only 'fints' is supported."
          default: "fints"
        bank_code: { type: string, description: "Bankleitzahl (BLZ) or BIC" }
        username: { type: string, description: "Banking Login / Legitimations-ID" }
        pin: { type: string, description: "Banking PIN / Password (handled ephemerally)" }

    DateRange:
      type: object
      required: [from, to]
      properties:
        from: { type: string, format: date, example: '2023-10-01' }
        to: { type: string, format: date, example: '2023-10-31' }

    FetchTransactionsRequest:
      type: object
      required: [connection, iban, date_range]
      properties:
        connection: { $ref: '#/components/schemas/BankConnection' }
        iban: { type: string, description: "Target account IBAN" }
        date_range: { $ref: '#/components/schemas/DateRange' }
        session_id: { type: string, nullable: true, description: "If resuming a TAN challenge" }
        tan_response: { type: string, nullable: true, description: "The TAN provided by the user" }

    Transaction:
      type: object
      properties:
        id: { type: string }
        booking_date: { type: string, format: date }
        value_date: { type: string, format: date }
        amount: { type: number, format: float }
        currency: { type: string }
        applicant_name: { type: string }
        purpose: { type: string }

    TransactionResponse:
      type: object
      properties:
        status: { type: string, enum: [SUCCESS, CHALLENGE_REQUIRED] }
        transactions:
          type: array
          items: { $ref: '#/components/schemas/Transaction' }
        challenge:
          type: object
          description: Populated if 2FA/TAN is required
          properties:
            session_id: { type: string }
            type: { type: string }
            media_data: { type: string }
6. Admin Service Layout (Control Plane)The Admin Service is physically isolated from the Gateway and governs overarching business logic:6.1. API Key & Security ManagementLifecycle: Generates, rotates, and revokes API keys.The Redis Push: Upon creation, keys are cryptographically hashed (Argon2) and saved to Postgres. The Admin Service simultaneously pushes the active hash to Redis.6.2. User & Subscription Management (Billing)Simple Subscriptions: Relies on PayPal's Subscriptions API for flat-rate billing.Event Webhooks: Listens to BILLING.SUBSCRIPTION.ACTIVATED and CANCELLED webhooks. Upon cancellation, the Admin service toggles the database flag and evicts the key hash from Redis.6.3. Institute Directory ManagementCentralized Configuration: Exposes internal tools to map Bank Codes (BLZ) to supported protocols (FinTS, PSD2) and connection URLs. Pushes updates directly to Redis for the Gateway to utilize.6.4. Legal Audit & ObservabilityAudit Viewer: Provides a read-only dashboard for administrators to review the IP-based Legal Audit Logs for compliance and abuse mitigation.7. Implementation RoadmapPhase 1: Gateway Core & InfrastructureProvision the monorepo structure.Build the src/gateway FastAPI skeleton and Redis integration.Implement the /transactions/fetch endpoint (supporting protocol: fints).Implement log-scrubbing middleware to guarantee PIN ephemerality.Phase 2: Control Plane & gRPC IntegrationInitialize the PostgreSQL schema in src/admin for Users and API keys.Define the .proto contracts for internal validation.Implement the Admin Service key generation, hashing, and Redis-push logic.Implement the gRPC KeyValidationService fallback on both services.Phase 3: Driver Refactor (SWEN Integration)Refactor the GeldstromAdapter in the SWEN backend to adopt a fetch pattern instead of sync.Implement the RemoteGeldstromDriver capable of resuming decoupled 2FA sessions.Phase 4: Commercialization & LaunchIntegrate simple PayPal Subscriptions into the Admin Service.Set up GitHub Actions for transparent image building and wire up the /system/version provenance endpoint.