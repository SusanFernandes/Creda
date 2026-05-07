/**
 * creda_next/src/app/api/backend/[...path]/route.ts
 *
 * Reverse-proxy any request to the FastAPI backend, injecting the Clerk user
 * identity as the `x-user-id` / `x-user-email` headers that FastAPI's
 * `get_auth()` dependency expects.
 *
 * Browser → /api/backend/<path>  →  this handler  →  BACKEND_API_URL/<path>
 *
 * This eliminates all CORS issues (same-origin) and is the only place where
 * the Clerk JWT is verified server-side before forwarding to FastAPI.
 */

import { auth } from '@clerk/nextjs/server';
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL =
  (process.env.BACKEND_API_URL ?? 'http://localhost:8001').replace(/\/$/, '');

// Headers that must not be forwarded to the backend
const HOP_BY_HOP = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailers',
  'transfer-encoding',
  'upgrade',
  'host',
]);

async function proxyRequest(
  req: NextRequest,
  params: Promise<{ path: string[] }>,
): Promise<NextResponse> {
  // Await params — required in Next.js 15
  const { path } = await params;
  const pathSegment = path.join('/');
  const search = req.nextUrl.search ?? '';
  const backendUrl = `${BACKEND_URL}/${pathSegment}${search}`;

  // Resolve Clerk auth (server-side — no token leaves the browser)
  const { userId, sessionClaims } = await auth();

  // Build forwarded headers
  const forwardHeaders = new Headers();
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      forwardHeaders.set(key, value);
    }
  });

  // Inject backend auth headers from Clerk session
  if (userId) {
    forwardHeaders.set('x-user-id', userId);
    const email =
      (sessionClaims?.email as string | undefined) ??
      (sessionClaims?.['primary_email_address'] as string | undefined) ??
      '';
    forwardHeaders.set('x-user-email', email);
  }

  // Forward the request body (handles JSON, multipart, etc.)
  const hasBody = req.method !== 'GET' && req.method !== 'HEAD';
  const body = hasBody ? await req.blob() : undefined;

  let backendRes: Response;
  try {
    backendRes = await fetch(backendUrl, {
      method: req.method,
      headers: forwardHeaders,
      body,
      redirect: 'manual',
      // @ts-expect-error — Node 18+ duplex required when body is a ReadableStream
      duplex: 'half',
    });
  } catch (err) {
    console.error('[proxy] Backend unreachable:', backendUrl, err);
    return NextResponse.json(
      { detail: 'Backend service unavailable.' },
      { status: 503 },
    );
  }

  // Pass response headers through
  const responseHeaders = new Headers();
  backendRes.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });

  return new NextResponse(backendRes.body, {
    status: backendRes.status,
    headers: responseHeaders,
  });
}

// Export all HTTP methods
type RouteContext = { params: Promise<{ path: string[] }> };

export function GET(req: NextRequest, ctx: RouteContext) {
  return proxyRequest(req, ctx.params);
}
export function POST(req: NextRequest, ctx: RouteContext) {
  return proxyRequest(req, ctx.params);
}
export function PUT(req: NextRequest, ctx: RouteContext) {
  return proxyRequest(req, ctx.params);
}
export function PATCH(req: NextRequest, ctx: RouteContext) {
  return proxyRequest(req, ctx.params);
}
export function DELETE(req: NextRequest, ctx: RouteContext) {
  return proxyRequest(req, ctx.params);
}
