"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Brain, Search, Sparkles, Layers } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-border bg-card/90 backdrop-blur-xl">
        <div className="container mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-xl">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/stash-mark.svg" alt="ContentStash" className="h-9 w-9 rounded-[10px] shadow-[0_8px_24px_oklch(24%_0.03_75_/_0.09)]" />
            <span className="text-foreground">Stash</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link href="/register">
              <Button>Get Started</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center pt-20 overflow-hidden">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute inset-x-0 top-0 h-96 bg-[radial-gradient(circle_at_8%_-8%,oklch(88%_0.075_166_/_0.52),transparent_34%),linear-gradient(180deg,oklch(99%_0.006_83),transparent_72%)]" />
        </div>

        <div className="container mx-auto px-6 relative z-10 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-card border border-border mb-8 shadow-sm">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span className="text-sm text-muted-foreground">Your AI-Powered Second Brain</span>
            </div>

            <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight mb-8">
              <span className="text-foreground">Remember Everything.</span>
              <br />
              <span className="text-muted-foreground">Rediscover Instantly.</span>
            </h1>

            <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto mb-12 leading-relaxed">
              Stash transforms your scattered bookmarks into a searchable, chat-ready knowledge base. Stop losing context and start building insights.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/register">
                <Button size="lg" className="h-14 px-8 text-lg rounded-full hover:scale-105 transition-all">
                  Start Stashing Free <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <Link href="/login">
                <Button variant="secondary" size="lg" className="h-14 px-8 text-lg rounded-full">
                  View Demo
                </Button>
              </Link>
            </div>
          </motion.div>

          {/* Hero Visual */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 1 }}
            className="mt-20 relative max-w-5xl mx-auto"
          >
            <div className="relative rounded-2xl overflow-hidden border border-border shadow-2xl bg-card">
              <div className="p-4 border-b border-border flex items-center gap-2 bg-muted">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/50" />
                  <div className="w-3 h-3 rounded-full bg-amber-500/50" />
                  <div className="w-3 h-3 rounded-full bg-green-500/50" />
                </div>
                <div className="flex-1 text-center text-xs text-muted-foreground font-mono">stash.app/library</div>
              </div>
              <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
                {/* Mock Cards */}
                {[1, 2, 3].map((i) => (
                  <div key={i} className="bg-background border border-border rounded-xl p-4 h-48 flex flex-col">
                    <div className="w-8 h-8 rounded-lg bg-muted mb-3" />
                    <div className="h-4 w-3/4 bg-muted rounded mb-2" />
                    <div className="h-3 w-full bg-muted rounded mb-1" />
                    <div className="h-3 w-2/3 bg-muted rounded" />
                    <div className="mt-auto flex gap-2">
                      <div className="h-5 w-12 bg-[oklch(92.5%_0.055_166)] rounded-full" />
                      <div className="h-5 w-12 bg-muted rounded-full" />
                    </div>
                  </div>
                ))}
              </div>
              {/* Chat Overlay Mock */}
              <div className="absolute bottom-8 right-8 w-80 bg-card border border-border rounded-xl shadow-2xl p-4 hidden md:block animate-float">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-6 h-6 bg-[oklch(92.5%_0.055_166)] rounded-md flex items-center justify-center">
                    <Sparkles className="w-3 h-3 text-[oklch(36%_0.085_166)]" />
                  </div>
                  <span className="text-sm font-bold">Ask Stash</span>
                </div>
                <div className="bg-muted rounded-lg p-3 mb-3 text-xs text-muted-foreground">
                  Based on your saved articles, good design prioritizes function over form...
                </div>
                <div className="h-8 bg-background rounded-md border border-border" />
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-32 relative">
        <div className="container mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold mb-6">Why Stash?</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              More than just bookmarks. Stash is an intelligent layer for your digital life.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <FeatureCard
              icon={<Brain className="w-8 h-8 text-primary" />}
              title="AI-Powered Organization"
              description="Automatically tags and categorizes your content so you don't have to. Spend less time filing and more time reading."
            />
            <FeatureCard
              icon={<Search className="w-8 h-8 text-primary" />}
              title="Chat with Your Library"
              description="Ask questions and get answers grounded in your saved content. It's like having a conversation with your bookmarks."
            />
            <FeatureCard
              icon={<Layers className="w-8 h-8 text-primary" />}
              title="Context Preservation"
              description="Save not just the link, but the key takeaways. Add personal notes and highlights that stick with the content."
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 relative overflow-hidden">
        <div className="container mx-auto px-6 relative z-10 text-center">
          <h2 className="text-4xl md:text-6xl font-bold mb-8">Ready to build your second brain?</h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Join thousands of knowledge workers who are taking control of their information diet.
          </p>
          <Link href="/register">
            <Button size="lg" className="h-16 px-10 text-xl rounded-full hover:scale-105 transition-all">
              Get Started for Free
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border bg-card">
        <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2 font-bold text-lg">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/stash-mark.svg" alt="ContentStash" className="h-7 w-7 rounded-md" />
            <span className="text-foreground">Stash</span>
          </div>
          <div className="text-muted-foreground text-sm">
            © iceTopia Productions. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="group p-8 rounded-2xl bg-card border border-border hover:bg-[oklch(99.2%_0.006_83)] hover:border-[oklch(77%_0.024_83)] transition-all duration-300 hover:-translate-y-2 shadow-sm">
      <div className="w-16 h-16 rounded-full bg-[oklch(92.5%_0.055_166)] flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
        {icon}
      </div>
      <h3 className="text-2xl font-bold mb-4 text-foreground group-hover:text-[oklch(48%_0.12_166)] transition-colors">{title}</h3>
      <p className="text-muted-foreground leading-relaxed">
        {description}
      </p>
    </div>
  );
}
