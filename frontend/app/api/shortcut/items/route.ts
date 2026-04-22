import { NextRequest, NextResponse } from 'next/server';
import { getServerApiUrl } from '@/lib/server-api';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

function shortcutAuthRequiredResponse(detail: string, backendStatus = 401) {
  return NextResponse.json(
    {
      ok: false,
      success: false,
      code: 'AUTH_REQUIRED',
      auth_required: true,
      requires_login: true,
      retryable: true,
      backend_status: backendStatus,
      detail,
    },
    {
      // Shortcuts' "Get Contents of URL" can stop the workflow on non-2xx
      // responses before the shortcut can inspect the JSON body and re-login.
      status: 200,
      headers: {
        'Cache-Control': 'no-store',
      },
    }
  );
}

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

  try {
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

    if (response.status === 401 || response.status === 403) {
      return shortcutAuthRequiredResponse(
        'Your ContentStash sign-in expired. Please sign in again to continue saving.',
        response.status
      );
    }

    return new NextResponse(responseBody, {
      status: response.status,
      headers: {
        'Cache-Control': 'no-store',
        'Content-Type': contentType,
      },
    });
  } catch (error) {
    console.error('Shortcut save proxy failed:', error);

    return NextResponse.json(
      {
        detail: 'The shortcut save proxy could not reach the backend API.',
      },
      {
        status: 502,
        headers: {
          'Cache-Control': 'no-store',
        },
      }
    );
  }
}
