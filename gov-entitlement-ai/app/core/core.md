Core Module Documentation (app/core)

1. Overview

The core module acts as the foundation layer of the entire Hybrid RAG system.

It is responsible for:
    Centralized configuration management
    Database connection handling (PostgreSQL)
    OCR environment setup (Tesseract)

This module ensures that all downstream components (ingestion, retrieval, generation) operate on a consistent and controlled environment.

2. Architecture & Flow

High-Level Flow

            .env / System Environment
                      ↓
                config.py
                      ↓
        ┌─────────────┴─────────────┐
        ↓                           ↓
 database.py                 ocr_config.py
        ↓                           ↓
 DB Connections              OCR Engine Setup

Execution Flow
    .env variables are loaded via dotenv
    Settings class initializes all configurations
    Database pool is created using DATABASE_URL
    OCR configuration is initialized when required
    Other modules import settings, get_db_conn(), and OCR config

3. Libraries Used & Justification

3.1 pydantic_settings.BaseSettings
Why used:
    Structured configuration management
    Type validation for environment variables

Role:
    Acts as a strongly-typed configuration layer
    Prevents runtime errors due to missing/malformed env variables

Why not plain .env access everywhere?
    Leads to scattered configuration logic
    No validation or type safety
    Hard to debug in production

3.2 python-dotenv (load_dotenv)
Why used:
    Loads environment variables from .env file during development

Role:
    Bridges local development and production environments

Why not rely only on OS environment variables?
    Local development becomes inconsistent
    Harder onboarding for team members

3.3 psycopg2 + ThreadedConnectionPool
Why used:
    Native PostgreSQL adapter with connection pooling support

Role:
    Efficient DB connection reuse
    Prevents overhead of creating connections per request

Why ThreadedConnectionPool specifically?
    Suitable for multi-threaded environments (e.g., FastAPI backend)

Why not alternatives?
| Alternative    | Reason Not Used                                          |
| -------------- | -------------------------------------------------------- |
| SQLAlchemy ORM | Adds abstraction overhead; less control over raw queries |
| asyncpg        | Requires async architecture redesign                     |
| sqlite         | Not scalable for production                              |

3.4 pytesseract
Why used:
    Python wrapper over Tesseract OCR engine

Role:
    Enables text extraction from scanned documents

Why Tesseract?
    Open-source
    Supports multilingual OCR (critical for Indian documents)

Why not alternatives?
| Alternative       | Reason Not Used                        |
| ----------------- | -------------------------------------- |
| Google Vision API | Paid, requires internet                |
| AWS Textract      | Expensive, vendor lock-in              |
| EasyOCR           | Less accurate for structured documents |

3.5 os
Why used:
    File path construction
    Environment variable handling

Role:
    Ensures cross-platform compatibility (though partially violated—see limitations)

4. Design Decisions & Strategies

4.1 Centralized Configuration Pattern
    All configs live in one place (Settings)
    Avoids duplication across modules

Impact:
    Easier debugging
    Cleaner imports
    Single source of truth

4.2 Property-based DATABASE_URL
    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

Why:
    Dynamic construction from individual components
    Avoids hardcoding full connection string

4.3 Connection Pooling Strategy
    Pre-initialized global pool
    Shared across application

Why:
    Reduces latency
    Prevents connection exhaustion

4.4 Explicit OCR Configuration Layer
    Hardcoded paths + controlled initialization

Why:
    Ensures deterministic OCR behavior
    Avoids runtime misconfiguration

5. Advantages

System-Level Benefits
    Consistency: Single config source across modules
    Performance: DB pooling reduces connection overhead
    Scalability-ready: PostgreSQL + pooling supports production load
    Multilingual OCR: Supports Hindi + Marathi + English
    Separation of concerns: Config, DB, OCR are decoupled

6. Limitations / Trade-offs (Critical)

6.1 Hardcoded OCR Paths (Major Issue)
    C:/Program Files/Tesseract-OCR/

Windows-specific
Breaks in:
    Linux servers
    Docker containers
    Cloud deployment

6.2 Mixed Config Strategy
    DB_USER: str = os.getenv(...)
    Mixing BaseSettings + os.getenv
    Redundant and defeats full power of Pydantic

6.3 No Connection Cleanup Strategy
    Pool created globally
    No graceful shutdown handling

6.4 No Retry / Fault Tolerance
    sys.exit(1)
    DB connection failure terminates system
    Not production resilient

6.5 Sync DB Layer
    psycopg2 is synchronous
    Limits scalability under high concurrency

7. Alternatives & Trade-offs

DB Layer
| Option             | Pros             | Cons                    |
| ------------------ | ---------------- | ----------------------- |
| psycopg2 (current) | Stable, simple   | Blocking                |
| asyncpg            | High performance | Requires async refactor |
| SQLAlchemy         | Abstraction      | Less control            |

OCR Layer
| Option              | Pros                  | Cons             |
| ------------------- | --------------------- | ---------------- |
| Tesseract (current) | Free, offline         | Setup complexity |
| Google Vision       | Accurate              | Cost             |
| AWS Textract        | Structured extraction | Expensive        |

Config System
| Option             | Pros         | Cons                  |
| ------------------ | ------------ | --------------------- |
| Pydantic (current) | Typed, clean | Slight learning curve |
| YAML config        | Readable     | No validation         |
| Raw env            | Simple       | Error-prone           |

8. Future Improvements

High Priority
    Replace hardcoded OCR paths with environment variables
    Fully migrate to Pydantic config (remove os.getenv)
    Add DB retry logic

Medium Priority
    Move to async DB (asyncpg)
    Add connection health checks
    Replace print with structured logging

Advanced
    Config versioning
    Multi-environment support (dev/staging/prod)
    Secret management (Vault, AWS Secrets Manager)

9. Key Takeaways
This module is well-structured but not production-hardened

Strong foundation with:
    Config centralization
    Connection pooling
    OCR abstraction

However:
    Portability issues exist
    Some design inconsistencies need fixing
    Scalability can be improved

10. Non-Technical Summary (For Stakeholders)

This module ensures the system:
    Connects reliably to the database
    Reads documents in multiple Indian languages
    Runs consistently across the application

It forms the base infrastructure layer of the AI system