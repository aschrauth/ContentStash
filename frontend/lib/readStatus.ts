const READ_OVERRIDES_KEY = 'contentstash_read_overrides';

type ReadOverrides = Record<string, boolean>;

function parseReadOverrides(raw: string | null): ReadOverrides {
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object') return {};

    const normalized: ReadOverrides = {};
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (typeof value === 'boolean') {
        normalized[key] = value;
      }
    }
    return normalized;
  } catch {
    return {};
  }
}

export function getReadOverrides(): ReadOverrides {
  if (typeof window === 'undefined') return {};
  return parseReadOverrides(window.localStorage.getItem(READ_OVERRIDES_KEY));
}

export function getReadOverride(itemId: string): boolean | undefined {
  const overrides = getReadOverrides();
  return overrides[itemId];
}

export function setReadOverride(itemId: string, isRead: boolean): void {
  if (typeof window === 'undefined') return;
  const overrides = getReadOverrides();
  overrides[itemId] = isRead;
  window.localStorage.setItem(READ_OVERRIDES_KEY, JSON.stringify(overrides));
}

export function resolveItemReadState(itemId: string, serverIsRead: boolean): boolean {
  const override = getReadOverride(itemId);
  return typeof override === 'boolean' ? override : serverIsRead;
}
