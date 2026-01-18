"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Brain, Search, Sparkles, Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-x-hidden">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/10 bg-slate-950/80 backdrop-blur-xl">
        <div className="container mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-xl">
            <div className="w-8 h-8 bg-gradient-to-br from-violet-600 to-cyan-500 rounded-lg flex items-center justify-center shadow-lg shadow-violet-500/20">
              <span className="text-white text-lg">S</span>
            </div>
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
              Stash
            </span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login">
              <Button variant="ghost" className="text-slate-300 hover:text-white">Sign In</Button>
            </Link>
            <Link href="/register">
              <Button className="shadow-lg shadow-violet-500/20">Get Started</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center pt-20 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-violet-600/20 rounded-full blur-[120px] animate-pulse-glow" />
          <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-cyan-500/20 rounded-full blur-[120px] animate-pulse-glow" style={{ animationDelay: '2s' }} />
          <div className="absolute top-[40%] left-[40%] w-[30%] h-[30%] bg-fuchsia-500/10 rounded-full blur-[100px] animate-pulse-glow" style={{ animationDelay: '4s' }} />
        </div>

        <div className="container mx-auto px-6 relative z-10 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8 backdrop-blur-sm">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span className="text-sm text-slate-300">Your AI-Powered Second Brain</span>
            </div>
            
            <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight mb-8">
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-white via-violet-200 to-cyan-200">
                Remember Everything.
              </span>
              <br />
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-slate-400 via-slate-200 to-slate-400">
                Rediscover Instantly.
              </span>
            </h1>

            <p className="text-xl md:text-2xl text-slate-400 max-w-3xl mx-auto mb-12 leading-relaxed">
              Stash transforms your scattered bookmarks into a searchable, chat-ready knowledge base. Stop losing context and start building insights.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/register">
                <Button size="lg" className="h-14 px-8 text-lg rounded-full shadow-xl shadow-violet-500/30 hover:shadow-violet-500/40 hover:scale-105 transition-all">
                  Start Stashing Free <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <Link href="/login">
                <Button variant="secondary" size="lg" className="h-14 px-8 text-lg rounded-full border-white/10 hover:bg-white/10">
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
            <div className="relative rounded-2xl overflow-hidden border border-white/10 shadow-2xl shadow-violet-500/20 bg-[#0f172a]/80 backdrop-blur-xl">
              <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent pointer-events-none" />
              <div className="p-4 border-b border-white/10 flex items-center gap-2 bg-white/5">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/50" />
                  <div className="w-3 h-3 rounded-full bg-amber-500/50" />
                  <div className="w-3 h-3 rounded-full bg-green-500/50" />
                </div>
                <div className="flex-1 text-center text-xs text-slate-500 font-mono">stash.app/library</div>
              </div>
              <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
                {/* Mock Cards */}
                {[1, 2, 3].map((i) => (
                  <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4 h-48 flex flex-col">
                    <div className="w-8 h-8 rounded-lg bg-white/10 mb-3" />
                    <div className="h-4 w-3/4 bg-white/10 rounded mb-2" />
                    <div className="h-3 w-full bg-white/5 rounded mb-1" />
                    <div className="h-3 w-2/3 bg-white/5 rounded" />
                    <div className="mt-auto flex gap-2">
                      <div className="h-5 w-12 bg-violet-500/20 rounded-full" />
                      <div className="h-5 w-12 bg-cyan-500/20 rounded-full" />
                    </div>
                  </div>
                ))}
              </div>
              {/* Chat Overlay Mock */}
              <div className="absolute bottom-8 right-8 w-80 bg-[#1e293b] border border-white/10 rounded-xl shadow-2xl p-4 hidden md:block animate-float">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-6 h-6 bg-violet-600 rounded-md flex items-center justify-center">
                    <Sparkles className="w-3 h-3 text-white" />
                  </div>
                  <span className="text-sm font-bold">Ask Stash</span>
                </div>
                <div className="bg-white/5 rounded-lg p-3 mb-3 text-xs text-slate-300">
                  Based on your saved articles, good design prioritizes function over form...
                </div>
                <div className="h-8 bg-white/5 rounded-md border border-white/10" />
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
            <p className="text-xl text-slate-400 max-w-2xl mx-auto">
              More than just bookmarks. Stash is an intelligent layer for your digital life.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <FeatureCard 
              icon={<Brain className="w-8 h-8 text-violet-400" />}
              title="AI-Powered Organization"
              description="Automatically tags and categorizes your content so you don't have to. Spend less time filing and more time reading."
            />
            <FeatureCard 
              icon={<Search className="w-8 h-8 text-cyan-400" />}
              title="Chat with Your Library"
              description="Ask questions and get answers grounded in your saved content. It's like having a conversation with your bookmarks."
            />
            <FeatureCard 
              icon={<Layers className="w-8 h-8 text-fuchsia-400" />}
              title="Context Preservation"
              description="Save not just the link, but the key takeaways. Add personal notes and highlights that stick with the content."
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-violet-900/20" />
        <div className="container mx-auto px-6 relative z-10 text-center">
          <h2 className="text-4xl md:text-6xl font-bold mb-8">Ready to build your second brain?</h2>
          <p className="text-xl text-slate-400 mb-12 max-w-2xl mx-auto">
            Join thousands of knowledge workers who are taking control of their information diet.
          </p>
          <Link href="/register">
            <Button size="lg" className="h-16 px-10 text-xl rounded-full shadow-2xl shadow-violet-500/40 hover:scale-105 transition-all">
              Get Started for Free
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-white/10 bg-slate-950">
        <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2 font-bold text-lg">
            <div className="w-6 h-6 bg-gradient-to-br from-violet-600 to-cyan-500 rounded-md flex items-center justify-center">
              <span className="text-white text-xs">S</span>
            </div>
            <span className="text-slate-300">Stash</span>
          </div>
          <div className="text-slate-500 text-sm">
            © 2024 Stash Inc. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="group p-8 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all duration-300 hover:-translate-y-2">
      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
        {icon}
      </div>
      <h3 className="text-2xl font-bold mb-4 text-white group-hover:text-violet-300 transition-colors">{title}</h3>
      <p className="text-slate-400 leading-relaxed">
        {description}
      </p>
    </div>
  );
}

