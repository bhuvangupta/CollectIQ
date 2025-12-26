import { HTMLAttributes, forwardRef } from 'react'
import clsx from 'clsx'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
  glow?: boolean
  glass?: boolean
  animate?: boolean
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, padding = 'md', hover = false, glow = false, glass = false, animate = false, children, ...props }, ref) => {
    const paddingStyles = {
      none: '',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
    }

    return (
      <div
        ref={ref}
        className={clsx(
          'rounded-2xl transition-all duration-300 ease-snappy',
          glass
            ? 'bg-white/70 backdrop-blur-xl border border-light-200/60 shadow-glass'
            : 'bg-white border border-light-200/80 shadow-card',
          paddingStyles[padding],
          hover && 'hover:shadow-card-hover hover:border-light-300 hover:-translate-y-1 cursor-pointer',
          glow && 'hover:border-primary-300/60 hover:shadow-card-glow',
          animate && 'animate-fade-in-up',
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

export const CardHeader = ({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={clsx('border-b border-light-200/60 pb-4 mb-4', className)} {...props}>
    {children}
  </div>
)

export const CardTitle = ({ className, children, ...props }: HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={clsx('text-lg font-semibold text-light-900', className)} {...props}>
    {children}
  </h3>
)

export const CardDescription = ({ className, children, ...props }: HTMLAttributes<HTMLParagraphElement>) => (
  <p className={clsx('text-sm text-light-500 mt-1', className)} {...props}>
    {children}
  </p>
)

export const CardContent = ({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={clsx('', className)} {...props}>
    {children}
  </div>
)

export const CardFooter = ({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={clsx('border-t border-light-200/60 pt-4 mt-4 flex items-center justify-end gap-3', className)} {...props}>
    {children}
  </div>
)

export default Card
