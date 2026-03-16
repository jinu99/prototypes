# express-api-kit

[![npm version](https://img.shields.io/npm/v/express-api-kit.svg)](https://www.npmjs.com/package/express-api-kit)
[![Build Status](https://github.com/alexchen/express-api-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/alexchen/express-api-kit/actions)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Downloads](https://img.shields.io/npm/dm/express-api-kit.svg)](https://www.npmjs.com/package/express-api-kit)

A batteries-included toolkit for building production-ready REST APIs with Express. Handles routing, validation, error handling, and authentication so you can focus on your business logic.

## Features

- **Declarative Routing** — Define routes with a clean, decorator-inspired syntax
- **Request Validation** — Built-in schema validation powered by Zod
- **Authentication Middleware** — JWT and API key authentication out of the box
- **Rate Limiting** — Configurable per-route rate limiting with Redis or in-memory stores
- **Structured Logging** — Pino-based request logging with correlation IDs
- **Error Handling** — Consistent error responses following RFC 7807 (Problem Details)
- **OpenAPI Generation** — Auto-generate OpenAPI 3.1 specs from your route definitions
- **TypeScript First** — Full type safety across routes, middleware, and handlers

## Installation

```bash
npm install express-api-kit
```

Or with Yarn:

```bash
yarn add express-api-kit
```

### Requirements

- Node.js >= 18.0.0
- TypeScript >= 5.0 (optional but recommended)

## Quick Start

```typescript
import { createApp, route, z } from 'express-api-kit';

const app = createApp({
  prefix: '/api/v1',
  logging: true,
  cors: { origin: '*' },
});

const userSchema = z.object({
  name: z.string().min(1),
  email: z.string().email(),
});

app.register(
  route.get('/users', async (req, res) => {
    const users = await db.users.findMany();
    res.json({ data: users });
  }),

  route.post('/users', {
    body: userSchema,
    handler: async (req, res) => {
      const user = await db.users.create(req.validated.body);
      res.status(201).json({ data: user });
    },
  }),

  route.get('/users/:id', async (req, res) => {
    const user = await db.users.findById(req.params.id);
    if (!user) throw new NotFoundError('User not found');
    res.json({ data: user });
  }),
);

app.listen(3000, () => {
  console.log('API running at http://localhost:3000');
});
```

## API Reference

### `createApp(options)`

Creates a new application instance.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `prefix` | `string` | `'/'` | Global route prefix |
| `logging` | `boolean` | `false` | Enable request logging |
| `cors` | `CorsOptions \| boolean` | `false` | CORS configuration |
| `rateLimit` | `RateLimitOptions` | `undefined` | Global rate limiting |

### `route.get(path, handler)` / `route.post(...)` / etc.

Define a route handler. Accepts either a handler function directly or an options object:

```typescript
// Simple handler
route.get('/health', (req, res) => res.json({ status: 'ok' }));

// With validation and middleware
route.post('/items', {
  body: itemSchema,
  middleware: [authenticate],
  handler: async (req, res) => { /* ... */ },
});
```

### `authenticate(options)`

Middleware for JWT or API key authentication.

```typescript
import { authenticate } from 'express-api-kit';

app.use(authenticate({
  strategy: 'jwt',
  secret: process.env.JWT_SECRET,
  exclude: ['/health', '/login'],
}));
```

### Error Classes

| Class | Status | Description |
|-------|--------|-------------|
| `NotFoundError` | 404 | Resource not found |
| `ValidationError` | 422 | Request validation failed |
| `UnauthorizedError` | 401 | Missing or invalid credentials |
| `ForbiddenError` | 403 | Insufficient permissions |
| `ConflictError` | 409 | Resource conflict |

## Configuration

You can configure the app using environment variables or a config file:

```bash
# .env
EAK_PORT=3000
EAK_LOG_LEVEL=info
EAK_RATE_LIMIT_WINDOW=60000
EAK_RATE_LIMIT_MAX=100
```

Or programmatically:

```typescript
import { configure } from 'express-api-kit';

configure({
  port: 3000,
  logLevel: 'info',
  rateLimit: { windowMs: 60_000, max: 100 },
});
```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) before submitting a PR.

1. Fork the repository
2. Create your feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes using [Conventional Commits](https://www.conventionalcommits.org/)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/alexchen/express-api-kit.git
cd express-api-kit
npm install
npm run dev
```

### Running Tests

```bash
npm test           # Run all tests
npm run test:watch # Watch mode
npm run test:cov   # With coverage
```

## License

Licensed under the [Apache License 2.0](LICENSE). See the LICENSE file for details.

---

Built with care by [Alex Chen](https://github.com/alexchen) and [contributors](https://github.com/alexchen/express-api-kit/graphs/contributors).
