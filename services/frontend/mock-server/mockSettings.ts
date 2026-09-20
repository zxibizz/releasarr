import type {
  ConnectionTestResult,
  DownloadCategoriesResponse,
  IndexerCategoriesResponse,
  QualityProfilesResponse,
  SettingFieldInfo,
  SettingsResponse,
  SettingsSection,
} from '../src/types';

interface MockField {
  key: string;
  section: SettingsSection;
  kind: SettingFieldInfo['kind'];
  is_secret?: boolean;
  requires_restart?: boolean;
  choices?: string[];
  locked?: boolean;
}

/**
 * The mock's settings registry, mirroring the backend's
 * `src/settings/registry.py`. `prowlarr_api_key` is seeded locked so the
 * environment-pinned, read-only state is visible in the mock UI.
 */
const FIELDS: MockField[] = [
  { key: 'release_missing_grace_seconds', section: 'general', kind: 'int' },
  { key: 'max_regrabs_per_indexer_per_execution', section: 'tasks', kind: 'int' },
  { key: 'regrab_indexer_delay_seconds', section: 'tasks', kind: 'float' },
  { key: 'sonarr_url', section: 'services', kind: 'str' },
  { key: 'sonarr_api_key', section: 'services', kind: 'str', is_secret: true },
  { key: 'sonarr_quality_profile_id', section: 'services', kind: 'int_optional' },
  { key: 'radarr_url', section: 'services', kind: 'str' },
  { key: 'radarr_api_key', section: 'services', kind: 'str', is_secret: true },
  { key: 'radarr_quality_profile_id', section: 'services', kind: 'int_optional' },
  { key: 'prowlarr_url', section: 'services', kind: 'str' },
  { key: 'prowlarr_api_key', section: 'services', kind: 'str', is_secret: true, locked: true },
  { key: 'prowlarr_categories', section: 'services', kind: 'str_list' },
  { key: 'qbittorrent_url', section: 'services', kind: 'str' },
  { key: 'qbittorrent_username', section: 'services', kind: 'str' },
  { key: 'qbittorrent_password', section: 'services', kind: 'str', is_secret: true },
  { key: 'qbittorrent_save_path', section: 'services', kind: 'str_optional' },
  { key: 'qbittorrent_category', section: 'services', kind: 'str_optional' },
  { key: 'qbittorrent_tag_prefix', section: 'services', kind: 'str_optional' },
  { key: 'qbittorrent_paused', section: 'services', kind: 'bool' },
  { key: 'auth_access_token_ttl_seconds', section: 'network', kind: 'int', requires_restart: true },
  { key: 'auth_refresh_token_ttl_seconds', section: 'network', kind: 'int', requires_restart: true },
  { key: 'auth_refresh_remember_ttl_seconds', section: 'network', kind: 'int', requires_restart: true },
  { key: 'auth_refresh_reuse_grace_seconds', section: 'network', kind: 'int', requires_restart: true },
  { key: 'auth_cookie_name', section: 'network', kind: 'str', requires_restart: true },
  { key: 'auth_cookie_path', section: 'network', kind: 'str', requires_restart: true },
  { key: 'auth_cookie_secure', section: 'network', kind: 'bool', requires_restart: true },
  { key: 'auth_cookie_samesite', section: 'network', kind: 'str', requires_restart: true, choices: ['lax', 'strict', 'none'] },
  { key: 'auth_max_failed_logins', section: 'network', kind: 'int' },
  { key: 'auth_lockout_seconds', section: 'network', kind: 'int' },
  { key: 'prowlarr_timeout', section: 'network', kind: 'float' },
  { key: 'prowlarr_search_timeout', section: 'network', kind: 'float' },
  { key: 'prowlarr_search_retries', section: 'network', kind: 'int' },
  { key: 'prowlarr_search_concurrency', section: 'network', kind: 'int' },
  { key: 'qbittorrent_timeout', section: 'network', kind: 'float' },
  { key: 'default_page_size', section: 'network', kind: 'int' },
  { key: 'max_page_size', section: 'network', kind: 'int' },
  { key: 'tvdb_base_url', section: 'metadata', kind: 'str' },
  { key: 'tvdb_api_key', section: 'metadata', kind: 'str', is_secret: true },
  { key: 'tmdb_base_url', section: 'metadata', kind: 'str' },
  { key: 'tmdb_api_key', section: 'metadata', kind: 'str', is_secret: true },
  { key: 'metadata_languages', section: 'metadata', kind: 'str_list' },
  { key: 'log_level', section: 'logging', kind: 'str', choices: ['DEBUG', 'INFO', 'WARNING', 'ERROR'] },
  { key: 'log_json', section: 'logging', kind: 'bool' },
  { key: 'log_history_files', section: 'logging', kind: 'int' },
];

const values: Record<string, Record<string, unknown>> = {
  general: { release_missing_grace_seconds: 900 },
  services: {
    sonarr_url: 'http://sonarr:8989/api/v3',
    sonarr_api_key: 'sonarr-key',
    sonarr_quality_profile_id: null,
    radarr_url: 'http://radarr:7878/api/v3',
    radarr_api_key: 'radarr-key',
    radarr_quality_profile_id: null,
    prowlarr_url: 'http://prowlarr:9696/api/v1',
    prowlarr_api_key: 'prowlarr-key',
    prowlarr_categories: ['5000', '2000'],
    qbittorrent_url: 'http://qbittorrent:8080/api/v2',
    qbittorrent_username: 'admin',
    qbittorrent_password: 'secret',
    qbittorrent_save_path: '/downloads',
    qbittorrent_category: 'releasarr',
    qbittorrent_tag_prefix: 'releasarr',
    qbittorrent_paused: false,
  },
  network: {
    auth_access_token_ttl_seconds: 900,
    auth_refresh_token_ttl_seconds: 86400,
    auth_refresh_remember_ttl_seconds: 2592000,
    auth_refresh_reuse_grace_seconds: 15,
    auth_cookie_name: 'releasarr_refresh',
    auth_cookie_path: '/api/auth',
    auth_cookie_secure: true,
    auth_cookie_samesite: 'lax',
    auth_max_failed_logins: 10,
    auth_lockout_seconds: 900,
    prowlarr_timeout: 20,
    prowlarr_search_timeout: 10,
    prowlarr_search_retries: 1,
    prowlarr_search_concurrency: 5,
    qbittorrent_timeout: 15,
    default_page_size: 20,
    max_page_size: 100,
  },
  metadata: {
    tvdb_base_url: 'https://api4.thetvdb.com/v4',
    tvdb_api_key: 'tvdb-key',
    tmdb_base_url: 'https://api.themoviedb.org/3',
    tmdb_api_key: 'tmdb-key',
    metadata_languages: ['eng', 'rus'],
  },
  tasks: { max_regrabs_per_indexer_per_execution: 20, regrab_indexer_delay_seconds: 2 },
  logging: { log_level: 'INFO', log_json: false, log_history_files: 3 },
};

export function getSettings(): SettingsResponse {
  const fields: SettingFieldInfo[] = FIELDS.map((f) => ({
    key: f.key,
    section: f.section,
    kind: f.kind,
    is_secret: f.is_secret ?? false,
    requires_restart: f.requires_restart ?? false,
    locked: f.locked ?? false,
    choices: f.choices ?? [],
  }));
  return {
    values,
    fields,
    locked_keys: FIELDS.filter((f) => f.locked).map((f) => f.key),
    pending_restart_keys: [],
  };
}

export function updateSettingsSection(
  section: string,
  patch: Record<string, unknown>,
): SettingsResponse {
  if (values[section]) {
    Object.assign(values[section], patch);
  }
  return getSettings();
}

export function testConnection(integration: string): ConnectionTestResult {
  // qBittorrent fails in the mock so both outcomes are demonstrable.
  const success = integration !== 'qbittorrent';
  return {
    integration,
    success,
    detail: success ? null : 'Could not reach the configured URL',
  };
}

export function getQualityProfiles(integration: string): QualityProfilesResponse {
  const profiles =
    integration === 'sonarr'
      ? [
          { id: 1, name: 'Any' },
          { id: 4, name: 'HD-1080p' },
          { id: 6, name: 'Ultra-HD' },
        ]
      : [
          { id: 2, name: 'Any' },
          { id: 5, name: 'HD Bluray + WEB' },
        ];
  return { profiles };
}

export function getIndexerCategories(): IndexerCategoriesResponse {
  return {
    categories: [
      { id: 2000, name: 'Movies' },
      { id: 2040, name: 'Movies/HD' },
      { id: 2045, name: 'Movies/UHD' },
      { id: 5000, name: 'TV' },
      { id: 5040, name: 'TV/HD' },
      { id: 5045, name: 'TV/UHD' },
    ],
  };
}

export function getDownloadCategories(): DownloadCategoriesResponse {
  return { categories: ['movies', 'releasarr', 'tv'] };
}
