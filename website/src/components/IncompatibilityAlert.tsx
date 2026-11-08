import React from 'react';
import { AlertTriangle, Info, ShieldAlert } from 'lucide-react';

interface IncompatibilityAlertProps {
  type?: 'warning' | 'error' | 'info';
  title: string;
  children: React.ReactNode;
  className?: string;
}

export const IncompatibilityAlert: React.FC<IncompatibilityAlertProps> = ({
  type = 'warning',
  title,
  children,
  className = ''
}) => {
  const styles = {
    warning: {
      container: 'bg-amber-950/40 border-amber-600/50 text-amber-200',
      icon: <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />,
      titleColor: 'text-amber-300'
    },
    error: {
      container: 'bg-rose-950/40 border-rose-600/50 text-rose-200',
      icon: <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0" />,
      titleColor: 'text-rose-300'
    },
    info: {
      container: 'bg-sky-950/40 border-sky-600/50 text-sky-200',
      icon: <Info className="w-5 h-5 text-sky-400 shrink-0" />,
      titleColor: 'text-sky-300'
    }
  }[type];

  return (
    <div className={`p-4 rounded-lg border flex items-start gap-3 text-sm leading-relaxed ${styles.container} ${className}`}>
      {styles.icon}
      <div className="flex-1">
        <h4 className={`font-semibold mb-1 ${styles.titleColor}`}>{title}</h4>
        <div className="text-xs sm:text-sm opacity-90">{children}</div>
      </div>
    </div>
  );
};

export default IncompatibilityAlert;
