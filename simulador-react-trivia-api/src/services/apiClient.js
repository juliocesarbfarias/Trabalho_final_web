// src/services/apiClient.js

// --- CONFIGURAÇÃO DA API EXTERNA (The Trivia API) ---
const FALLBACK = "https://the-trivia-api.com/v2";
const BASE_URL_EXTERNAL = (import.meta?.env?.VITE_API_BASE_URL) || FALLBACK;

function buildUrl(path) {
  if (/^https?:\/\//i.test(path)) return path;
  const base = (BASE_URL_EXTERNAL || "").replace(/\/$/, "");
  const p = (path || "").replace(/^\//, "");
  return `${base}/${p}`;
}

/**
 * [LEGADO] Função para buscar dados da API EXTERNA (Trivia API)
 * Usada pelo useQuestions.js
 */
export async function apiGet(path, { signal, headers } = {}) {
  const url = buildUrl(path);
  console.log("-> GET EXTERNAL:", url);
  const res = await fetch(url, {
    method: "GET",
    headers: { "Accept": "application/json", ...(headers || {}) },
    signal
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

// --- CONFIGURAÇÃO DA NOSSA API (FastAPI) ---
// O endereço do seu backend Python
const FASTAPI_BASE_URL = "http://127.0.0.1:8000"; 

/**
 * Faz uma requisição POST para o nosso backend (Gera simulado).
 * Envia o TOKEN se estiver logado.
 */
export async function apiPost(path, body, { signal, headers } = {}) {
  const url = `${FASTAPI_BASE_URL}${path}`;
  console.log("-> POST:", url, body);
  
  // 1. PEGA O TOKEN
  const token = localStorage.getItem("authToken");

  // 2. CABEÇALHOS
  const authHeaders = {
    "Accept": "application/json",
    "Content-Type": "application/json",
  };

  // 3. INSERE O TOKEN
  if (token) {
    authHeaders["Authorization"] = `Bearer ${token}`;
  }
  
  const res = await fetch(url, {
    method: "POST",
    headers: {
      ...authHeaders,
      ...(headers || {})
    },
    body: JSON.stringify(body),
    signal
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    try {
      const errJson = JSON.parse(text);
      if (errJson.detail) {
        throw new Error(`Erro do Servidor: ${errJson.detail}`);
      }
    } catch (e) {}
    throw new Error(`HTTP ${res.status} - ${res.statusText} | ${text}`);
  }
  
  return res.json();
}

/**
 * Faz o Login (POST form-urlencoded).
 */
export async function apiLogin(username, password) {
  const url = `${FASTAPI_BASE_URL}/token`;
  
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);

  console.log("-> LOGIN:", url);

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: params,
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => null);
    if (errData && errData.detail) {
      throw new Error(errData.detail);
    }
    throw new Error(`HTTP ${res.status} - Falha no login`);
  }

  return res.json();
}

/**
 * Faz GET no nosso backend (Histórico, Detalhes).
 * Envia o TOKEN se estiver logado.
 */
export async function apiGetInternal(path) {
  const url = `${FASTAPI_BASE_URL}${path}`;
  
  const token = localStorage.getItem("authToken"); 

  const headers = {
    "Accept": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    method: "GET",
    headers: headers,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Erro HTTP ${res.status}: ${text}`);
  }

  return res.json();
}