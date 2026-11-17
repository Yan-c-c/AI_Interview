import common from '@ohos.app.ability.common';
import preferences from '@ohos.data.preferences';
import { AuthUser, HistoryRecord } from '../models/Models';
import { GENERATED_BACKEND_BASE_URL, GENERATED_BACKEND_CANDIDATE_URLS } from './GeneratedConfig';

const STORE_NAME = 'ai_interview_lite_store';
const KEY_TOKEN = 'auth_token';
const KEY_USER = 'auth_user';
const KEY_HISTORY = 'history_records';
const KEY_BASE_URL = 'backend_base_url';
const KEY_AUTO_SAVE = 'auto_save_history';

export const DEFAULT_BASE_URL = GENERATED_BACKEND_BASE_URL;
export const DEFAULT_BASE_URLS: string[] = GENERATED_BACKEND_CANDIDATE_URLS;

export function normalizeBaseUrl(raw: string): string {
  const value = raw.trim();
  if (value.length === 0) {
    return DEFAULT_BASE_URL;
  }
  if (value.toLowerCase().startsWith('http://') || value.toLowerCase().startsWith('https://')) {
    return trimTrailingSlash(value);
  }
  return trimTrailingSlash(`http://${value}`);
}

export function getBackendCandidateUrls(preferred: string): string[] {
  const urls: string[] = [];
  appendBackendUrl(urls, preferred);
  for (let i = 0; i < DEFAULT_BASE_URLS.length; i++) {
    appendBackendUrl(urls, DEFAULT_BASE_URLS[i]);
  }
  appendBackendUrl(urls, DEFAULT_BASE_URL);
  return urls;
}

function appendBackendUrl(urls: string[], raw: string): void {
  const url = normalizeBaseUrl(raw);
  if (url.length === 0) {
    return;
  }
  for (let i = 0; i < urls.length; i++) {
    if (urls[i] === url) {
      return;
    }
  }
  urls.push(url);
}

function trimTrailingSlash(value: string): string {
  if (value.endsWith('/')) {
    return value.slice(0, value.length - 1);
  }
  return value;
}

export class StorageService {
  static async getToken(context: common.Context): Promise<string> {
    const pref = await StorageService.getStore(context);
    if (!pref) {
      return '';
    }
    try {
      return String(await pref.get(KEY_TOKEN, ''));
    } catch (_err) {
      return '';
    }
  }

  static async saveToken(context: common.Context, token: string): Promise<void> {
    const pref = await StorageService.getStore(context);
    if (!pref) {
      return;
    }
    try {
      await pref.put(KEY_TOKEN, token);
      await pref.flush();
    } catch (_err) {
    }
  }

  static async getUser(context: common.Context): Promise<AuthUser | undefined> {
    const pref = await StorageService.getStore(context);
    if (!pref) {
      return undefined;
    }
    let raw = '';
    try {
      raw = String(await pref.get(KEY_USER, ''));
    } catch (_err) {
      return undefined;
    }
    if (!raw) {
      return undefined;
    }
    try {
      return JSON.parse(raw) as AuthUser;
    } catch (_err) {
      return undefined;
    }
  }

  static async saveUser(context: common.Context, user: AuthUser): Promise<void> {
    const pref = await StorageService.getStore(context);
    if (!pref) {
      return;
    }
    try {
      await pref.put(KEY_USER, JSON.stringify(user));
      await pref.flush();
    } catch (_err) {
    }
  }

  static async clearSession(context: common.Context): Promise<void> {
    const pref = await StorageService.getStore(context);
    if (!pref) {
      return;
    }
    try {
      await pref.delete(KEY_TOKEN);
      await pref.delete(KEY_USER);
      await pref.flush();
    } catch (_err) {
    }
  }

  static async getBaseUrl(context: common.Context): Promise<string> {
    const pref = await StorageService.getStore(context);
    if (!pref) {
      return DEFAULT_BASE_URL;
    }
    try {
      return normalizeBaseUrl(String(await pref.get(KEY_BASE_URL, DEFAULT_BASE_URL)));
    } catch (_err) {
      return DEFAULT_BASE_URL;
    }
  }

  static async saveBaseUrl(context: common.Context, baseUrl: string): Promise<void> {
    const pref = await StorageService.getStore(context);
    if (!pref) {
      return;
    }
    try {
      await pref.put(KEY_BASE_URL, normalizeBaseUrl(baseUrl));
      await pref.flush();
    } catch (_err) {
    }
  }

  static async getAutoSave(context: common.Context): Promise<boolean> {
    const pref = await StorageService.getStore(context);
    if (!pref) {
      return true;
    }
    try {
      return Boolean(await pref.get(KEY_AUTO_SAVE, true));
    } catch (_err) {
      return true;
    }
  }

  static async saveAutoSave(context: common.Context, enabled: boolean): Promise<void> {
    const pref = await StorageService.getStore(context);
    if (!pref) {
      return;
    }
    try {
      await pref.put(KEY_AUTO_SAVE, enabled);
      await pref.flush();
    } catch (_err) {
    }
  }

  static async getHistory(context: common.Context): Promise<HistoryRecord[]> {
    const pref = await StorageService.getStore(context);
    if (!pref) {
      return [];
    }
    let raw = '[]';
    try {
      raw = String(await pref.get(KEY_HISTORY, '[]'));
    } catch (_err) {
      return [];
    }
    try {
      const records = JSON.parse(raw) as HistoryRecord[];
      return records;
    } catch (_err) {
      return [];
    }
  }

  static async saveHistory(context: common.Context, records: HistoryRecord[]): Promise<void> {
    const pref = await StorageService.getStore(context);
    if (!pref) {
      return;
    }
    try {
      await pref.put(KEY_HISTORY, JSON.stringify(records));
      await pref.flush();
    } catch (_err) {
    }
  }

  private static async getStore(context: common.Context): Promise<preferences.Preferences | undefined> {
    try {
      return await preferences.getPreferences(context, STORE_NAME);
    } catch (_err) {
      return undefined;
    }
  }
}
