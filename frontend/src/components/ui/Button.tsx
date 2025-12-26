import { ButtonHTMLAttributes, forwardRef } from 'react'
import clsx from 'clsx'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'ai'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  icon?: boolean
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, icon, children, disabled, ...props }, ref) => {
    const baseStyles = `
      inline-flex items-center justify-center font-medium rounded-xl
      transition-all duration-200 ease-snappy
      focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white
      disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none disabled:hover:transform-none
      active:scale-[0.98] active:duration-75
      select-none
    `

    const variants = {
      primary: `
        bg-gradient-to-r from-primary-500 to-primary-600 text-white
        shadow-btn shadow-primary-500/20
        hover:from-primary-600 hover:to-primary-700
        hover:shadow-btn-hover hover:shadow-primary-500/25
        hover:-translate-y-0.5
        focus:ring-primary-500 border border-primary-600/20
      `,
      secondary: `
        bg-white text-light-700 border border-light-200
        shadow-sm
        hover:bg-light-50 hover:text-light-900 hover:border-light-300
        hover:shadow-md hover:-translate-y-0.5
        focus:ring-light-400
      `,
      danger: `
        bg-gradient-to-r from-red-500 to-red-600 text-white
        shadow-btn shadow-red-500/20
        hover:from-red-600 hover:to-red-700
        hover:shadow-btn-hover hover:shadow-red-500/25
        hover:-translate-y-0.5
        focus:ring-red-500 border border-red-600/20
      `,
      ghost: `
        bg-transparent text-light-600
        hover:bg-light-100 hover:text-light-900
        focus:ring-light-400
      `,
      ai: `
        bg-gradient-to-r from-ai-500 to-ai-600 text-white
        shadow-btn shadow-ai-500/20
        hover:from-ai-600 hover:to-ai-700
        hover:shadow-btn-hover hover:shadow-ai-500/25
        hover:-translate-y-0.5
        focus:ring-ai-500 border border-ai-600/20
      `,
    }

    const sizes = {
      sm: icon ? 'p-2' : 'px-3 py-1.5 text-sm gap-1.5',
      md: icon ? 'p-2.5' : 'px-4 py-2.5 text-sm gap-2',
      lg: icon ? 'p-3' : 'px-6 py-3 text-base gap-2',
    }

    return (
      <button
        ref={ref}
        className={clsx(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button
