import React from 'react';

export type EvidenceType = 'measured' | 'partial' | 'analytical' | 'ready' | 'unknown';

interface EvidenceBadgeProps {
  status: EvidenceType;
  showIcon?: boolean;
  className?: string;
}

export const EvidenceBadge: React.FC<EvidenceBadgeProps> = ({ status, showIcon = true, className = '' }) => {
  const configs: Record<EvidenceType, { label: string; icon: string; classes: string; desc: string }> = {
    measured: {
      label: 'Measured',
      icon: '✓',
      classes: 'bg-[#E7F6F1] dark:bg-[#063826] text-[#0E7A5A] dark:text-[#34D399] border-[#0E7A5A]/30 dark:border-[#34D399]/40',
      desc: 'Empirically measured on physical hardware (GTX 1050 Ti)'
    },
    partial: {
      label: 'Partial',
      icon: '◐',
      classes: 'bg-[#FEF3C7] dark:bg-[#382806] text-[#B45309] dark:text-[#FBBF24] border-[#B45309]/30 dark:border-[#FBBF24]/40',
      desc: 'Incomplete campaign or interrupted pilot study'
    },
    analytical: {
      label: 'Analytical',
      icon: '∑',
      classes: 'bg-[#EEF2FF] dark:bg-[#181C38] text-[#4338CA] dark:text-[#818CF8] border-[#4338CA]/30 dark:border-[#818CF8]/40',
      desc: 'Theoretical model or roofline calculation; not hardware bus utilization'
    },
    ready: {
      label: 'Ready (Unmeasured)',
      icon: '⚙',
      classes: 'bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] border-[#E2E5E5] dark:border-[#242F32]',
      desc: 'Benchmark specification verified deterministically; no model run yet'
    },
    unknown: {
      label: 'Unknown',
      icon: '?',
      classes: 'bg-[#F5F5F3] dark:bg-[#182022] text-[#526063] dark:text-[#98A8AA] border-[#E2E5E5] dark:border-[#242F32]',
      desc: 'Unexplored / unmeasured in this research program'
    }
  };

  const cfg = configs[status] || configs.unknown;

  return (
    <span
      title={cfg.desc}
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-mono font-medium rounded-full border transition-colors ${cfg.classes} ${className}`}
    >
      {showIcon && <span className="text-[10px]">{cfg.icon}</span>}
      <span>{cfg.label}</span>
    </span>
  );
};

export default EvidenceBadge;
