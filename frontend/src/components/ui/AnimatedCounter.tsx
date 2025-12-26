import { useEffect, useState, useRef } from 'react';
import clsx from 'clsx';

interface AnimatedCounterProps {
  value: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  className?: string;
  onComplete?: () => void;
}

export function AnimatedCounter({
  value,
  duration = 1000,
  prefix = '',
  suffix = '',
  decimals = 0,
  className,
  onComplete,
}: AnimatedCounterProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const previousValue = useRef(0);
  const animationRef = useRef<number>();

  useEffect(() => {
    const startValue = previousValue.current;
    const endValue = value;
    const startTime = performance.now();

    setIsAnimating(true);

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Easing function (ease-out cubic)
      const easeOut = 1 - Math.pow(1 - progress, 3);

      const currentValue = startValue + (endValue - startValue) * easeOut;
      setDisplayValue(currentValue);

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        setDisplayValue(endValue);
        previousValue.current = endValue;
        setIsAnimating(false);
        onComplete?.();
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [value, duration, onComplete]);

  const formattedValue = displayValue.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  return (
    <span
      className={clsx(
        'inline-block tabular-nums transition-transform duration-200',
        isAnimating && 'scale-[1.02]',
        className
      )}
    >
      {prefix}
      {formattedValue}
      {suffix}
    </span>
  );
}

// Simpler hook version for custom implementations
export function useAnimatedCounter(
  targetValue: number,
  duration: number = 1000
): number {
  const [value, setValue] = useState(0);
  const previousValue = useRef(0);

  useEffect(() => {
    const startValue = previousValue.current;
    const endValue = targetValue;
    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);

      const currentValue = startValue + (endValue - startValue) * easeOut;
      setValue(currentValue);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setValue(endValue);
        previousValue.current = endValue;
      }
    };

    requestAnimationFrame(animate);
  }, [targetValue, duration]);

  return value;
}

// Percentage counter with circular progress indicator
interface PercentageCounterProps {
  value: number;
  size?: 'sm' | 'md' | 'lg';
  color?: 'primary' | 'accent' | 'ai' | 'warning' | 'danger';
  showLabel?: boolean;
  className?: string;
}

export function PercentageCounter({
  value,
  size = 'md',
  color = 'primary',
  showLabel = true,
  className,
}: PercentageCounterProps) {
  const animatedValue = useAnimatedCounter(value, 800);

  const sizes = {
    sm: { container: 'w-12 h-12', stroke: 3, text: 'text-xs' },
    md: { container: 'w-16 h-16', stroke: 4, text: 'text-sm' },
    lg: { container: 'w-20 h-20', stroke: 5, text: 'text-base' },
  };

  const colors = {
    primary: 'text-primary-500',
    accent: 'text-accent-500',
    ai: 'text-ai-500',
    warning: 'text-amber-500',
    danger: 'text-red-500',
  };

  const strokeColors = {
    primary: 'stroke-primary-500',
    accent: 'stroke-accent-500',
    ai: 'stroke-ai-500',
    warning: 'stroke-amber-500',
    danger: 'stroke-red-500',
  };

  const { container, stroke, text } = sizes[size];
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (animatedValue / 100) * circumference;

  return (
    <div className={clsx('relative', container, className)}>
      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          className="stroke-light-200"
          strokeWidth={stroke}
        />
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          className={clsx(strokeColors[color], 'transition-all duration-300')}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
        />
      </svg>
      {showLabel && (
        <div className={clsx('absolute inset-0 flex items-center justify-center', colors[color], text, 'font-semibold tabular-nums')}>
          {Math.round(animatedValue)}%
        </div>
      )}
    </div>
  );
}
