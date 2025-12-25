import { useForm } from 'react-hook-form'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useLogin } from '../hooks/useAuth'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import { SparklesIcon } from '@heroicons/react/24/outline'

interface LoginForm {
  email: string
  password: string
}

export default function Login() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const login = useLogin()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>()

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  const onSubmit = (data: LoginForm) => {
    login.mutate(data)
  }

  return (
    <div className="min-h-screen flex bg-light-50">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-primary-600 to-primary-800">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute inset-0" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, white 1px, transparent 0)', backgroundSize: '32px 32px' }} />
        </div>

        {/* Animated glow effects */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-white/10 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-accent-400/20 rounded-full blur-3xl animate-pulse-slow delay-1000" />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center px-16">
          <div className="flex items-center gap-4 mb-8">
            <div className="relative">
              <div className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center border border-white/30">
                <SparklesIcon className="w-8 h-8 text-white" />
              </div>
              <div className="absolute -inset-2 rounded-2xl bg-white/10 blur-lg -z-10" />
            </div>
            <span className="text-3xl font-bold text-white">
              CollectIQ
            </span>
          </div>

          <h1 className="text-4xl font-bold text-white mb-4">
            AI-Powered Collection Platform
          </h1>
          <p className="text-lg text-primary-100 mb-8 max-w-md">
            Automate your loan recovery with intelligent AI agents. Increase collection rates while improving borrower experience.
          </p>

          <div className="grid grid-cols-2 gap-6 max-w-md">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-white">Smart Calling</p>
                <p className="text-xs text-primary-200">AI voice agents</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-white">Analytics</p>
                <p className="text-xs text-primary-200">Real-time insights</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-white">Recovery</p>
                <p className="text-xs text-primary-200">Higher rates</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-white">Compliant</p>
                <p className="text-xs text-primary-200">RBI guidelines</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Login form */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center shadow-lg">
              <SparklesIcon className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-light-900">
              CollectIQ
            </span>
          </div>

          <div className="bg-white border border-light-200 rounded-2xl p-8 shadow-card">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-light-900">
                Welcome back
              </h2>
              <p className="mt-2 text-sm text-light-500">
                Sign in to access your dashboard
              </p>
            </div>

            <form className="space-y-5" onSubmit={handleSubmit(onSubmit)}>
              <Input
                id="email"
                type="email"
                label="Email address"
                placeholder="you@company.com"
                autoComplete="email"
                error={errors.email?.message}
                {...register('email', {
                  required: 'Email is required',
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: 'Invalid email address',
                  },
                })}
              />

              <Input
                id="password"
                type="password"
                label="Password"
                placeholder="Enter your password"
                autoComplete="current-password"
                error={errors.password?.message}
                {...register('password', {
                  required: 'Password is required',
                  minLength: {
                    value: 6,
                    message: 'Password must be at least 6 characters',
                  },
                })}
              />

              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    id="remember-me"
                    name="remember-me"
                    type="checkbox"
                    className="w-4 h-4 rounded border-light-300 bg-white text-primary-500 focus:ring-primary-500/20 focus:ring-offset-0"
                  />
                  <span className="text-sm text-light-500">Remember me</span>
                </label>

                <a href="#" className="text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors">
                  Forgot password?
                </a>
              </div>

              <Button
                type="submit"
                className="w-full"
                size="lg"
                loading={login.isPending}
              >
                Sign in
              </Button>
            </form>
          </div>

          <div className="mt-6 p-4 rounded-xl bg-light-100 border border-light-200">
            <p className="text-center text-sm text-light-500">
              Demo: <span className="text-light-700 font-medium">admin@collectiq.com</span> / <span className="text-light-700 font-medium">password123</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
