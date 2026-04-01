import Link from 'next/link';
import { headers } from 'next/headers';
import { ArrowRight, ExternalLink, Smartphone } from 'lucide-react';
import { Button } from '@/components/ui/Button';

function getAppOrigin(hostHeader: string | null, protoHeader: string | null) {
  if (!hostHeader) {
    return 'http://localhost:3000';
  }

  const protocol = protoHeader || (hostHeader.includes('localhost') ? 'http' : 'https');
  return `${protocol}://${hostHeader}`;
}

export default async function IOSShortcutPage() {
  const headerStore = await headers();
  const appOrigin = getAppOrigin(
    headerStore.get('x-forwarded-host') || headerStore.get('host'),
    headerStore.get('x-forwarded-proto')
  );
  const loginEndpoint = `${appOrigin}/api/shortcut/login`;
  const itemsEndpoint = `${appOrigin}/api/shortcut/items`;

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-10 px-6 py-16">
        <div className="space-y-6">
          <Link
            href="/"
            className="inline-flex items-center text-sm text-slate-400 transition-colors hover:text-white"
          >
            <ArrowRight className="mr-2 h-4 w-4 rotate-180" />
            Back to Stash
          </Link>

          <div className="inline-flex items-center gap-3 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-sm text-cyan-200">
            <Smartphone className="h-4 w-4" />
            iOS Shortcut Setup
          </div>

          <div className="space-y-4">
            <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              Install once. Sign in once. Save from anywhere.
            </h1>
            <p className="max-w-3xl text-lg leading-8 text-slate-300">
              The shortcut no longer needs your raw backend URL or a JWT copied out of dev tools.
              Point it at your Stash app URL, let the shortcut log in with your email and password,
              and send saves through the shortcut proxy endpoints below.
            </p>
          </div>
        </div>

        <section className="grid gap-4 rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl shadow-cyan-950/20">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-400">
              Use This Base URL In The Shortcut
            </p>
            <p className="mt-3 break-all rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 font-mono text-sm text-cyan-200">
              {appOrigin}
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
              <p className="text-sm font-medium text-white">Login endpoint</p>
              <p className="mt-2 break-all font-mono text-xs text-slate-300">{loginEndpoint}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
              <p className="text-sm font-medium text-white">Save endpoint</p>
              <p className="mt-2 break-all font-mono text-xs text-slate-300">{itemsEndpoint}</p>
            </div>
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-3">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-400">1. Install</p>
            <p className="mt-4 text-base leading-7 text-slate-200">
              Share a shortcut that already has your Stash app URL filled in. For production, that
              means users should not have to edit any URLs at all.
            </p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-400">2. Sign In</p>
            <p className="mt-4 text-base leading-7 text-slate-200">
              On first run, prompt for email and password, call the login endpoint, and store the
              returned token in the shortcut&apos;s local config file.
            </p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-400">3. Save</p>
            <p className="mt-4 text-base leading-7 text-slate-200">
              Every save goes through the save endpoint using the stored bearer token. If the token
              expires, the shortcut can transparently prompt for login again.
            </p>
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
          <h2 className="text-2xl font-semibold text-white">Recommended Shortcut Logic</h2>
          <ol className="mt-4 space-y-3 text-sm leading-7 text-slate-300">
            <li>1. Store one configurable value: the Stash app origin shown above.</li>
            <li>2. On first run, ask for email and password.</li>
            <li>3. POST those credentials to the login endpoint and save the returned token.</li>
            <li>4. POST shared URLs to the save endpoint with `Authorization: Bearer &lt;token&gt;`.</li>
            <li>5. If save returns `401`, clear the stored token, re-run login, and retry once.</li>
          </ol>
        </section>

        <div className="flex flex-wrap gap-3">
          <Link href="/login">
            <Button className="shadow-lg shadow-cyan-500/20">
              Sign In To Stash
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
          <Link href="/register">
            <Button variant="secondary">
              Create Account
              <ExternalLink className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>
    </main>
  );
}
