import type { Metadata } from 'next';
import { Newsreader, Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';

const newsreader = Newsreader({
  variable: '--font-newsreader',
  subsets: ['latin'],
  style: ['normal', 'italic'],
  weight: ['400', '500', '600']
});

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
  weight: ['400', '500', '600', '700']
});

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-jetbrains-mono',
  subsets: ['latin'],
  weight: ['400', '500', '600']
});

export const metadata: Metadata = {
  title: 'SLM-Limits | Small Language Model Empirical Frontier Research',
  description:
    'Scientific research platform evaluating the practical limits, efficiency frontiers, memory budgets, and security posture of Small Language Models (0.5B–4B) on constrained 4 GiB VRAM hardware.',
  keywords: [
    'Small Language Models',
    'SLM',
    'LLM Benchmark',
    'GTX 1050 Ti',
    'VRAM Constraints',
    'llama.cpp',
    'Artificial Analysis',
    'Epoch AI',
    'Pareto Frontier'
  ]
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${newsreader.variable} ${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[#FBFBFA] dark:bg-[#0A0E0F] text-[#0E1415] dark:text-[#F2F5F5] font-sans selection:bg-[#006D77]/20 selection:text-[#006D77] dark:selection:bg-[#2DD4BF]/20 dark:selection:text-[#2DD4BF]">
        {/* Skip Navigation Link for Keyboard Accessibility (WCAG 2.2 AA) */}
        <a href="#main-content" className="skip-link">
          Skip to main research content
        </a>
        <Navbar />
        <main
          id="main-content"
          tabIndex={-1}
          role="main"
          className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-7 focus:outline-none"
        >
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
