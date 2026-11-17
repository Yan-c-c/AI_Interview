import http from '@ohos.net.http';
import { AssistantPayload, AuthSession, AuthUser } from '../models/Models';

type JsonValue = Object | string | number | boolean | null | undefined;

interface LoginRequest {
  email: string;
  password: string;
}

interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

interface ChatRequest {
  message: string;
  session_id: string;
}

interface RequestHeader {
  'Content-Type': string;
  'Accept': string;
  'Authorization'?: string;
}

interface ApiErrorDetail {
  message?: string;
}

interface ApiErrorResponse {
  message?: string;
  detail?: ApiErrorDetail;
}

interface AuthResponse {
  token?: string;
  user?: AuthUser;
}

interface AssistantResult {
  summary?: JsonValue;
  versions?: JsonValue;
  email?: JsonValue;
  questions?: JsonValue;
  strategy?: JsonValue;
  career_plan?: JsonValue;
  qa_analysis?: JsonValue;
}

interface AssistantResponse {
  success?: boolean;
  intent?: string;
  agent?: string;
  message?: string;
  result?: AssistantResult;
}

export class ApiClient {
  static async findReachableBaseUrl(candidates: string[]): Promise<string> {
    for (let i = 0; i < candidates.length; i++) {
      const candidate = candidates[i];
      if (candidate.length === 0) {
        continue;
      }
      const healthy = await ApiClient.health(candidate);
      if (healthy) {
        return candidate;
      }
    }
    return '';
  }

  static async health(baseUrl: string): Promise<boolean> {
    try {
      await ApiClient.requestText(baseUrl, '/health', 'GET', '', undefined, 1200, 1500);
      return true;
    } catch (_err) {
      return false;
    }
  }

  static async login(baseUrl: string, email: string, password: string): Promise<AuthSession> {
    const body: LoginRequest = {
      email: email,
      password: password
    };
    const data = await ApiClient.requestJson(baseUrl, '/api/admin/auth/login', 'POST', '', body) as AuthResponse;
    return {
      token: data.token ?? '',
      user: data.user as AuthUser
    };
  }

  static async register(baseUrl: string, name: string, email: string, password: string): Promise<AuthSession> {
    const body: RegisterRequest = {
      name: name,
      email: email,
      password: password
    };
    const data = await ApiClient.requestJson(baseUrl, '/api/admin/auth/register', 'POST', '', body) as AuthResponse;
    return {
      token: data.token ?? '',
      user: data.user as AuthUser
    };
  }

  static async me(baseUrl: string, token: string): Promise<AuthUser> {
    const data = await ApiClient.requestJson(baseUrl, '/api/admin/auth/me', 'GET', token) as AuthResponse;
    return data.user as AuthUser;
  }

  static async chat(baseUrl: string, token: string, message: string, sessionId: string): Promise<AssistantPayload> {
    const body: ChatRequest = {
      message: message,
      session_id: sessionId
    };
    const data = await ApiClient.requestJson(baseUrl, '/api/assistant/chat', 'POST', token, body) as AssistantResponse;
    const messageText = data.message ?? '';
    const result = data.result;
    const rawJson = ApiClient.safePrettyJson(data);
    const displayText = ApiClient.renderAssistantText(messageText, result, rawJson);
    return {
      success: data.success ?? false,
      intent: data.intent ?? 'unknown',
      agent: data.agent ?? '',
      message: messageText,
      displayText: displayText,
      rawJson: rawJson
    };
  }

  private static async requestJson(
    baseUrl: string,
    path: string,
    method: string,
    token: string,
    body?: Object
  ): Promise<Object> {
    const responseText = await ApiClient.requestText(baseUrl, path, method, token, body);
    try {
      return JSON.parse(responseText) as Object;
    } catch (_err) {
      throw new Error('后端响应不是有效 JSON');
    }
  }

  private static requestText(
    baseUrl: string,
    path: string,
    method: string,
    token: string,
    body?: Object,
    connectTimeout: number = 15000,
    readTimeout: number = 120000
  ): Promise<string> {
    const url = ApiClient.joinUrl(baseUrl, path);
    const request = http.createHttp();
    const headers: RequestHeader = token.length > 0
      ? {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`
      }
      : {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    };
    const requestMethod = method === 'GET' ? http.RequestMethod.GET : http.RequestMethod.POST;
    const options: http.HttpRequestOptions = {
      method: requestMethod,
      header: headers,
      extraData: body ? JSON.stringify(body) : '',
      expectDataType: http.HttpDataType.STRING,
      connectTimeout: connectTimeout,
      readTimeout: readTimeout
    };
    return new Promise<string>((resolve, reject) => {
      request.request(url, options, (err, response) => {
        request.destroy();
        if (err) {
          reject(new Error(err.message || '网络请求失败'));
          return;
        }
        const status = response.responseCode;
        const text = String(response.result ?? '');
        if (status < 200 || status >= 300) {
          reject(new Error(ApiClient.extractErrorMessage(text, status)));
          return;
        }
        resolve(text);
      });
    });
  }

  private static joinUrl(baseUrl: string, path: string): string {
    const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${cleanBase}${cleanPath}`;
  }

  private static extractErrorMessage(raw: string, status: number): string {
    try {
      const data = JSON.parse(raw) as ApiErrorResponse;
      if (data.detail && data.detail.message && data.detail.message.length > 0) {
        return data.detail.message;
      }
      if (data.message && data.message.length > 0) {
        return data.message;
      }
    } catch (_err) {
    }
    return `请求失败：HTTP ${status}`;
  }

  private static renderAssistantText(message: string, result: AssistantResult | undefined, rawJson: string): string {
    const sections: string[] = [];
    if (message.length > 0) {
      sections.push(message);
    }
    if (result) {
      const summary = result.summary;
      if (summary) {
        sections.push(`摘要\n${ApiClient.safePrettyJson(summary)}`);
      }
      const versions = result.versions;
      if (versions) {
        sections.push(`生成版本\n${ApiClient.safePrettyJson(versions)}`);
      }
      const email = result.email;
      if (email) {
        sections.push(`邮件正文\n${ApiClient.safePrettyJson(email)}`);
      }
      const questions = result.questions;
      if (questions) {
        sections.push(`面试题\n${ApiClient.safePrettyJson(questions)}`);
      }
      const strategy = result.strategy;
      if (strategy) {
        sections.push(`谈薪策略\n${ApiClient.safePrettyJson(strategy)}`);
      }
      const plan = result.career_plan;
      if (plan) {
        sections.push(`职业计划\n${ApiClient.safePrettyJson(plan)}`);
      }
      const qa = result.qa_analysis;
      if (qa) {
        sections.push(`逐题分析\n${ApiClient.safePrettyJson(qa)}`);
      }
    }
    if (sections.length === 0) {
      sections.push(rawJson);
    }
    return sections.join('\n\n');
  }

  private static safePrettyJson(value: JsonValue): string {
    if (value === undefined || value === null) {
      return '';
    }
    try {
      return JSON.stringify(value, null, 2);
    } catch (_err) {
      return String(value);
    }
  }
}
