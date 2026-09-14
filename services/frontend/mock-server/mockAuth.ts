import { randomUUID } from 'crypto';

import type {
  ChangePasswordPayload,
  CreateServiceKeyPayload,
  CreateUserPayload,
  LoginPayload,
  ServiceApiKey,
  ServiceApiKeyCreated,
  SetupPayload,
  UpdateUserPayload,
  User,
} from '../src/types';

/** Thrown to short-circuit a route handler with a specific HTTP status. */
export class MockAuthError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

interface MockUserRecord extends User {
  password: string;
}

interface MockServiceKeyRecord extends ServiceApiKey {
  secret: string;
}

const users = new Map<string, MockUserRecord>();
const serviceKeys = new Map<string, MockServiceKeyRecord>();
// token -> user id. Refresh tokens rotate; access tokens do not expire in the mock.
const accessTokens = new Map<string, string>();
const refreshTokens = new Map<string, string>();

const now = () => new Date().toISOString();

function seed() {
  const admin: MockUserRecord = {
    id: 'admin',
    username: 'admin',
    display_name: 'Admin',
    password: 'admin',
    role: 'admin',
    is_active: true,
    can_view_all_requests: true,
    can_access_tasks: true,
    can_access_indexers: true,
    can_access_logs: true,
    allowed_root_folders: [],
    last_login_at: null,
    created_at: now(),
    updated_at: now(),
  };
  // A deliberately restricted second account, so the mock exercises the same
  // scoping the real backend applies: no tasks/indexers/logs, one allowed folder.
  const restricted: MockUserRecord = {
    id: 'user-1',
    username: 'user',
    display_name: 'Restricted User',
    password: 'user',
    role: 'user',
    is_active: true,
    can_view_all_requests: false,
    can_access_tasks: false,
    can_access_indexers: false,
    can_access_logs: false,
    allowed_root_folders: ['/media/movies'],
    last_login_at: null,
    created_at: now(),
    updated_at: now(),
  };
  users.set(admin.id, admin);
  users.set(restricted.id, restricted);
}

// MOCK_EMPTY_USERS=1 exercises the first-run setup screen against the mock server.
if (process.env.MOCK_EMPTY_USERS !== '1') {
  seed();
}

function toPublicUser({ password: _password, ...rest }: MockUserRecord): User {
  return rest;
}

function toPublicKey({ secret: _secret, ...rest }: MockServiceKeyRecord): ServiceApiKey {
  return rest;
}

function issueSession(user: MockUserRecord) {
  const accessToken = randomUUID();
  const refreshToken = randomUUID();
  accessTokens.set(accessToken, user.id);
  refreshTokens.set(refreshToken, user.id);
  user.last_login_at = now();
  return { access_token: accessToken, refresh_token: refreshToken, user: toPublicUser(user) };
}

function findByUsername(username: string): MockUserRecord | undefined {
  const needle = username.trim().toLowerCase();
  return [...users.values()].find((user) => user.username === needle);
}

function requireUser(userId: string): MockUserRecord {
  const user = users.get(userId);
  if (!user) {
    throw new MockAuthError(404, 'user_not_found', `User '${userId}' was not found`);
  }
  return user;
}

function guardLastAdmin(target: MockUserRecord, next: UpdateUserPayload) {
  if (target.role !== 'admin') return;
  const demoting = next.role !== undefined && next.role !== 'admin';
  const deactivating = next.is_active === false;
  if (!demoting && !deactivating) return;
  const remainingAdmins = [...users.values()].filter(
    (user) => user.id !== target.id && user.role === 'admin' && user.is_active,
  );
  if (remainingAdmins.length === 0) {
    throw new MockAuthError(409, 'last_admin', 'Cannot remove or demote the last active admin');
  }
}

export const mockAuth = {
  setupRequired: () => users.size === 0,

  completeSetup(payload: SetupPayload) {
    if (users.size > 0) {
      throw new MockAuthError(409, 'setup_complete', 'Setup has already been completed');
    }
    const admin: MockUserRecord = {
      id: randomUUID(),
      username: payload.username.trim().toLowerCase(),
      display_name: payload.display_name ?? null,
      password: payload.password,
      role: 'admin',
      is_active: true,
      can_view_all_requests: true,
      can_access_tasks: true,
      can_access_indexers: true,
      can_access_logs: true,
      allowed_root_folders: [],
      last_login_at: null,
      created_at: now(),
      updated_at: now(),
    };
    users.set(admin.id, admin);
    return issueSession(admin);
  },

  login(payload: LoginPayload) {
    const user = findByUsername(payload.username);
    if (!user || user.password !== payload.password) {
      throw new MockAuthError(401, 'invalid_credentials', 'Invalid username or password');
    }
    if (!user.is_active) {
      throw new MockAuthError(403, 'user_inactive', 'This account has been deactivated');
    }
    return issueSession(user);
  },

  refresh(refreshToken: string | undefined) {
    if (!refreshToken || !refreshTokens.has(refreshToken)) {
      throw new MockAuthError(401, 'invalid_refresh_token', 'Refresh token is invalid or expired');
    }
    const userId = refreshTokens.get(refreshToken)!;
    refreshTokens.delete(refreshToken);
    const user = users.get(userId);
    if (!user) {
      throw new MockAuthError(401, 'invalid_refresh_token', 'Refresh token is invalid or expired');
    }
    return issueSession(user);
  },

  logout(refreshToken: string | undefined) {
    if (refreshToken) {
      refreshTokens.delete(refreshToken);
    }
  },

  authenticate(authorizationHeader: string | undefined, apiKeyHeader: string | undefined) {
    if (authorizationHeader?.toLowerCase().startsWith('bearer ')) {
      const token = authorizationHeader.slice(7).trim();
      const userId = accessTokens.get(token);
      if (!userId) return null;
      return users.get(userId) ?? null;
    }
    if (apiKeyHeader) {
      const key = [...serviceKeys.values()].find((entry) => entry.secret === apiKeyHeader);
      if (!key || !key.is_active) return null;
      return users.get(key.user_id) ?? null;
    }
    return null;
  },

  listUsers: () => [...users.values()].sort((a, b) => a.username.localeCompare(b.username)).map(toPublicUser),

  getUser: (userId: string) => toPublicUser(requireUser(userId)),

  createUser(payload: CreateUserPayload) {
    if (findByUsername(payload.username)) {
      throw new MockAuthError(409, 'username_taken', `Username '${payload.username}' is already taken`);
    }
    const user: MockUserRecord = {
      id: randomUUID(),
      username: payload.username.trim().toLowerCase(),
      display_name: payload.display_name ?? null,
      password: payload.password,
      role: payload.role ?? 'user',
      is_active: payload.is_active ?? true,
      can_view_all_requests: payload.can_view_all_requests ?? false,
      can_access_tasks: payload.can_access_tasks ?? false,
      can_access_indexers: payload.can_access_indexers ?? false,
      can_access_logs: payload.can_access_logs ?? false,
      allowed_root_folders: payload.allowed_root_folders ?? [],
      last_login_at: null,
      created_at: now(),
      updated_at: now(),
    };
    users.set(user.id, user);
    return toPublicUser(user);
  },

  updateUser(userId: string, payload: UpdateUserPayload) {
    const user = requireUser(userId);
    guardLastAdmin(user, payload);
    Object.assign(user, {
      ...(payload.display_name !== undefined ? { display_name: payload.display_name } : {}),
      ...(payload.password ? { password: payload.password } : {}),
      ...(payload.role !== undefined ? { role: payload.role } : {}),
      ...(payload.is_active !== undefined ? { is_active: payload.is_active } : {}),
      ...(payload.can_view_all_requests !== undefined
        ? { can_view_all_requests: payload.can_view_all_requests }
        : {}),
      ...(payload.can_access_tasks !== undefined ? { can_access_tasks: payload.can_access_tasks } : {}),
      ...(payload.can_access_indexers !== undefined
        ? { can_access_indexers: payload.can_access_indexers }
        : {}),
      ...(payload.can_access_logs !== undefined ? { can_access_logs: payload.can_access_logs } : {}),
      ...(payload.allowed_root_folders !== undefined
        ? { allowed_root_folders: payload.allowed_root_folders }
        : {}),
      updated_at: now(),
    });
    return toPublicUser(user);
  },

  deleteUser(userId: string) {
    const user = requireUser(userId);
    if (user.role === 'admin') {
      const remainingAdmins = [...users.values()].filter(
        (candidate) => candidate.id !== user.id && candidate.role === 'admin' && candidate.is_active,
      );
      if (remainingAdmins.length === 0) {
        throw new MockAuthError(409, 'last_admin', 'Cannot remove the last active admin');
      }
    }
    users.delete(userId);
  },

  changeOwnPassword(userId: string, payload: ChangePasswordPayload) {
    const user = requireUser(userId);
    if (user.password !== payload.current_password) {
      throw new MockAuthError(401, 'invalid_credentials', 'Invalid username or password');
    }
    user.password = payload.new_password;
    user.updated_at = now();
  },

  listServiceKeys: () => [...serviceKeys.values()].map(toPublicKey),

  createServiceKey(payload: CreateServiceKeyPayload): ServiceApiKeyCreated {
    requireUser(payload.user_id);
    const secret = `rlsr_${randomUUID().replace(/-/g, '')}`;
    const record: MockServiceKeyRecord = {
      id: randomUUID(),
      name: payload.name,
      prefix: secret.slice(0, 12),
      secret,
      user_id: payload.user_id,
      is_active: true,
      expires_at: payload.expires_at ?? null,
      last_used_at: null,
      created_at: now(),
    };
    serviceKeys.set(record.id, record);
    return { key: toPublicKey(record), plaintext: secret };
  },

  revokeServiceKey(keyId: string) {
    if (!serviceKeys.delete(keyId)) {
      throw new MockAuthError(404, 'service_key_not_found', `Service key '${keyId}' was not found`);
    }
  },
};
