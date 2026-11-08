'use client';

import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface EChartWrapperProps {
  options: echarts.EChartsOption;
  height?: string | number;
  className?: string;
  onEvents?: Record<string, (params: any) => void>;
}

export const EChartWrapper: React.FC<EChartWrapperProps> = ({
  options,
  height = '400px',
  className = '',
  onEvents
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    const isDark = document.documentElement.classList.contains('dark');

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, isDark ? 'dark' : undefined, {
        renderer: 'canvas'
      });

      if (onEvents) {
        Object.entries(onEvents).forEach(([eventName, handler]) => {
          chartInstance.current?.on(eventName, handler);
        });
      }
    }

    const customOptions: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      textStyle: {
        fontFamily: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif'
      },
      ...options
    };

    chartInstance.current.setOption(customOptions, true);

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    // Observer for dark mode class toggles
    const observer = new MutationObserver(() => {
      if (!chartInstance.current || !chartRef.current) return;
      chartInstance.current.dispose();
      const currentDark = document.documentElement.classList.contains('dark');
      chartInstance.current = echarts.init(chartRef.current, currentDark ? 'dark' : undefined, {
        renderer: 'canvas'
      });
      if (onEvents) {
        Object.entries(onEvents).forEach(([eventName, handler]) => {
          chartInstance.current?.on(eventName, handler);
        });
      }
      chartInstance.current.setOption(customOptions, true);
    });

    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    return () => {
      window.removeEventListener('resize', handleResize);
      observer.disconnect();
    };
  }, [options, onEvents]);

  useEffect(() => {
    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, []);

  return (
    <div
      ref={chartRef}
      style={{ height: typeof height === 'number' ? `${height}px` : height, width: '100%' }}
      className={`relative min-h-[300px] ${className}`}
    />
  );
};

export default EChartWrapper;
