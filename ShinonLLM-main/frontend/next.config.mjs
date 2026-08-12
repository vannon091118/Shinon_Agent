const DEFAULT_BACKEND_ORIGIN = "http://localhost:3001";
const API_PROXY_BASE = "/api";

function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeOrigin(value) {
  if (typeof value !== "string") {
    return null;
  }

  try {
    const url = new URL(value.trim());
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return null;
    }
    return url.origin;
  } catch {
    return null;
  }
}

/**
 * Builds security HTTP headers, including a Content-Security-Policy that incorporates the provided backend origin.
 * @param {string} backendOrigin - The backend origin (e.g., "https://api.example.com") to allow in `connect-src` and its WebSocket equivalent.
 * @returns {Array<{key: string, value: string}>} An array of header objects suitable for use in Next.js `headers()`; the CSP restricts sources for scripts, styles, images, forms, frames, base URI, and connection targets (including the backend origin and its ws/wss equivalent).
 */
function buildSecurityHeaders(backendOrigin) {
  const connectSources = [
    "'self'",
    backendOrigin,
    backendOrigin.replace("http://", "ws://").replace("https://", "wss://"),
  ];

  return [
    {
      key: "Content-Security-Policy",
      value: [
        "default-src 'self'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "img-src 'self' data: blob:",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
        "style-src 'self' 'unsafe-inline'",
        `connect-src ${connectSources.join(" ")}`,
      ].join("; "),
    },
    { key: "X-Frame-Options", value: "DENY" },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
    { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
    { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
  ];
}

function buildRewrites(backendOrigin) {
  return [
    {
      source: `${API_PROXY_BASE}/:path*`,
      destination: `${backendOrigin}/:path*`,
    },
  ];
}

function buildNextConfig(backendOrigin) {
  const devAllowedOrigins = [
    "localhost",
    "127.0.0.1",
    "192.168.178.35",
  ];

  return {
    reactStrictMode: true,
    poweredByHeader: false,
    compress: true,
    trailingSlash: false,
    allowedDevOrigins: devAllowedOrigins,
    async headers() {
      return [
        {
          source: "/:path*",
          headers: buildSecurityHeaders(backendOrigin),
        },
      ];
    },
    async rewrites() {
      return buildRewrites(backendOrigin);
    },
  };
}

/**
 * Public helper required by the blueprint.
 * It validates optional caller input and returns a deterministic config bundle.
 */
export function nextconfigMain(input = {}) {
  if (!isPlainObject(input)) {
    return {
      ok: false,
      error: {
        code: "INVALID_UI_STATE",
        message: "nextconfigMain expects a plain input object.",
      },
    };
  }

  const backendOrigin = normalizeOrigin(input.backendOrigin) ?? DEFAULT_BACKEND_ORIGIN;
  const userText =
    typeof input.userText === "string" ? input.userText.trim() : "";
  const uiState = input.uiState;

  if (input.backendOrigin != null && normalizeOrigin(input.backendOrigin) == null) {
    return {
      ok: false,
      error: {
        code: "INVALID_UI_STATE",
        message: "backendOrigin must be an http(s) origin.",
      },
    };
  }

  if (input.userText != null && userText.length === 0) {
    return {
      ok: false,
      error: {
        code: "INVALID_UI_STATE",
        message: "userText must not be empty when provided.",
      },
    };
  }

  if (input.uiState != null && !isPlainObject(uiState)) {
    return {
      ok: false,
      error: {
        code: "INVALID_UI_STATE",
        message: "uiState must be a plain object when provided.",
      },
    };
  }

  return {
    ok: true,
    events: [
      {
        type: "NEXT_CONFIG_READY",
        target: "frontend",
        backendOrigin,
      },
    ],
    apiPayload: {
      proxyBase: API_PROXY_BASE,
      backendOrigin,
      proxyTarget: `${backendOrigin}/:path*`,
      uiState,
      userText,
    },
    config: buildNextConfig(backendOrigin),
    error: null,
  };
}

const defaultResult = nextconfigMain({});

if (!defaultResult.ok) {
  throw new Error(defaultResult.error.message);
}

export default defaultResult.config;
