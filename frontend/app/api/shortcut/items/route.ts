import { NextRequest, NextResponse } from 'next/server';
import { getServerApiUrl } from '@/lib/server-api';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  const authorization = request.headers.get('authorization');

  if (!authorization) {
    return NextResponse.json(
      { detail: 'Missing Authorization header' },
      {
        status: 401,
        headers: {
          'Cache-Control': 'no-store',
        },
      }
    );
  }

  const body = await request.text();

  const response = await fetch(getServerApiUrl('/items'), {
    method: 'POST',
    headers: {
      'Authorization': authorization,
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
