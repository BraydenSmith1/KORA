## Auth (JWT)

- Endpoints:
  - `POST /auth/register` { email, password, name?, regionId? } → returns `{ user, token }`
  - `POST /auth/login` { email, password } → returns `{ user, token }`
  - `POST /auth/pilot-login` { role: operator|anchor, password } → returns `{ user, role, token }`
  - `POST /auth/dev-login` { email, name?, regionId? } → returns `{ user, token, mode: 'dev' }`
- Send the token on subsequent requests: header `Authorization: Bearer <token>`.
- Legacy header `x-user-id` still works for now, but emits a warning.

### Environment
- Set `JWT_SECRET` in `.env` to a strong secret.
