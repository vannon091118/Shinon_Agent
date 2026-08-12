import { NextRequest, NextResponse } from "next/server";

const DEFAULT_BACKEND_ORIGIN = "http://127.0.0.1:3001";

function resolveBackendUrl(path: string): string {
  const configuredOrigin = process.env.BACKEND_ORIGIN?.trim()
    || process.env.NEXT_PUBLIC_BACKEND_ORIGIN?.trim()
    || DEFAULT_BACKEND_ORIGIN;
  const normalizedOrigin = configuredOrigin.replace(/\/+$/u, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedOrigin}${normalizedPath}`;
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = await request.text();
  const upstream = await fetch(resolveBackendUrl("/api/chat"), {
    method: "POST",
    headers: {
      "content-type": "application/json; charset=utf-8",
    },
    body,
    cache: "no-store",
  });

  const payload = await upstream.text();
  return new NextResponse(payload, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
