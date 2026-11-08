import React from 'react';

interface HardwareBadgeProps {
  className?: string;
  showDetails?: boolean;
}

export const HardwareBadge: React.FC<HardwareBadgeProps> = ({
  className = '',
  showDetails = true
}) => {
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-medium rounded-md border bg-[#E6F3F4] dark:bg-[#0D2C28] text-[#006D77] dark:text-[#2DD4BF] border-[#006D77]/25 dark:border-[#2DD4BF]/30 ${className}`}
      title="Hardware Testbed: NVIDIA GeForce GTX 1050 Ti (4096 MiB GDDR5, 112 GB/s, PVE CT 108)"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-[#006D77] dark:bg-[#2DD4BF]" aria-hidden="true" />
      <span className="font-semibold">GTX 1050 Ti</span>
      {showDetails && <span className="hidden sm:inline">· 4096 MiB GDDR5 · 112 GB/s</span>}
    </div>
  );
};

export default HardwareBadge;
