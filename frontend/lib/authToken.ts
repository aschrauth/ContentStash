export function getJwtExpirationMs(token: string): number | null {
  const [, payload] = token.split('.');

  if (!payload) {
    return null;
  }

  try {
    const normalizedPayload = payload.replace(/-/g, '+').replace(/_/g, '/');
    const paddedPayload = normalizedPayload.padEnd(
      normalizedPayload.length + ((4 - (normalizedPayload.length % 4)) % 4),
      '='
    );
    const decodedPayload = JSON.parse(atob(paddedPayload)) as { exp?: unknown };

    return typeof decodedPayload.exp === 'number' ? decodedPayload.exp * 1000 : null;
  } catch {
    return null;
  }
}

export function isJwtExpired(token: string, clockSkewMs = 30_000): boolean {
  const expiresAt = getJwtExpirationMs(token);

  return expiresAt !== null && expiresAt <= Date.now() + clockSkewMs;
}
