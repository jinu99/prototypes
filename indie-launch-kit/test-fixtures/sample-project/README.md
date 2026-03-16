# FastAPI Starter

> A batteries-included FastAPI project template with async support, auto-docs, and built-in auth.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)]()

## Features

- **Async-first** — Built on top of async/await for maximum performance
- **Auto-generated docs** — Swagger UI and ReDoc out of the box
- **JWT Authentication** — Secure token-based auth with refresh tokens
- **Database migrations** — Alembic integration for hassle-free schema changes
- **Testing suite** — pytest with async support and fixtures

## Getting Started

```bash
pip install fastapi-starter
```

### Configuration

Create a `.env` file:

```bash
DATABASE_URL=sqlite+aiosqlite:///./app.db
SECRET_KEY=your-secret-key
```

### Running

```bash
uvicorn app.main:app --reload
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | POST | Login and get JWT token |
| `/auth/register` | POST | Register new user |
| `/users/me` | GET | Get current user profile |

## Architecture

The project follows a clean architecture pattern:

```
app/
├── api/         # Route handlers
├── core/        # Config, security
├── models/      # SQLAlchemy models
├── schemas/     # Pydantic schemas
└── services/    # Business logic
```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## License

MIT License — see [LICENSE](LICENSE) for details.
