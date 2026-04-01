import { NextRequest, NextResponse } from 'next/server';
import { getServerApiUrl } from '@/lib/server-api';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const body = await request.text();

  const response = await fetch(getServerApiUrl('/auth/login'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
    cache: 'no-store',
  });

  const responseBody = await response.text();
  const contentType = response.headers.get('content-type') || 'application/json';

  return new NextResponse(responseBody, {
    status: response.status,
    headers: {
      'Cache-Control': 'no-store',
      'Content-Type': contentType,
    },
  });
}
