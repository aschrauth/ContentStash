import { NextRequest, NextResponse } from 'next/server';
import { getServerApiUrl } from '@/lib/server-api';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

function shortcutLoginFailureResponse(detail: string, code: string, backendStatus: number) {
  return NextResponse.json(
    {
      ok: false,
      success: false,
      code,
      retryable: backendStatus >= 500,
      backend_status: backendStatus,
      detail,
    },
    {
      // Keep login failures inspectable by Shortcuts instead of aborting the
      // workflow inside the network action.
      status: 200,
      headers: {
        'Cache-Control': 'no-store',
      },
    }
  );
}

export async function POST(request: NextRequest) {
  try {
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

    if (response.status === 401) {
      return shortcutLoginFailureResponse(
        'That email or password was not accepted. Please try signing in again.',
        'INVALID_CREDENTIALS',
        response.status
      );
    }

    if (response.status === 400 || response.status === 422) {
      return shortcutLoginFailureResponse(
        'The shortcut could not read the sign-in details. Please check the email and password fields.',
        'INVALID_LOGIN_REQUEST',
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
    console.error('Shortcut login proxy failed:', error);

    return NextResponse.json(
      {
        detail: 'The shortcut login proxy could not reach the backend API.',
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
