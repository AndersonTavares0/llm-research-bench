'use client';

import React, { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';

export const ThemeToggle: React.FC = () => {
  const [isDark, setIsDark] = useState<boolean>(false);
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
    setMounted(true);
    // Respect stored theme or default to light-first
    const stored = localStorage.getItem('theme');
    if (stored === 'dark') {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    } else {
      setIsDark(false);
      document.documentElement.classList.remove('dark');
    }
  }, []);

  const toggleTheme = () => {
    if (isDark) {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
      setIsDark(false);
    } else {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
      setIsDark(true);
    }
  };

  if (!mounted) {
    return <div className="w-8 h-8 rounded-md bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32]" />;
  }

  return (
    <button
      onClick={toggleTheme}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      className="p-1.5 rounded-md bg-[#FFFFFF] dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#F5F5F3] dark:hover:bg-[#182022] text-[#475456] dark:text-[#98A8AA] hover:text-[#0E1415] dark:hover:text-[#F2F5F5] transition-colors focus:outline-none focus:ring-2 focus:ring-[#006D77] dark:focus:ring-[#2DD4BF]"
    >
      {isDark ? (
        <Sun className="w-4 h-4 text-[#FBBF24]" aria-hidden="true" />
      ) : (
        <Moon className="w-4 h-4 text-[#006D77]" aria-hidden="true" />
      )}
    </button>
  );
};

export default ThemeToggle;
