import { NavLink } from 'react-router-dom'
import {
  HomeIcon,
  FolderIcon,
  UsersIcon,
  MegaphoneIcon,
  PhoneIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  SparklesIcon,
  ClipboardDocumentListIcon,
  MicrophoneIcon,
  PhoneArrowUpRightIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline'
import { useUIStore } from '../../stores/uiStore'
import { useAuthStore } from '../../stores/authStore'
import clsx from 'clsx'

const allNavigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Cases', href: '/cases', icon: FolderIcon },
  { name: 'Borrowers', href: '/borrowers', icon: UsersIcon },
  { name: 'Campaigns', href: '/campaigns', icon: MegaphoneIcon, roles: ['admin', 'manager'] },
  { name: 'Communications', href: '/communications', icon: PhoneIcon },
  { name: 'AI Intelligence', href: '/ai-intelligence', icon: CpuChipIcon, roles: ['admin', 'manager'] },
  { name: 'AI Demo', href: '/ai-demo', icon: MicrophoneIcon, roles: ['admin', 'manager'] },
  { name: 'AI Calls', href: '/ai-call-test', icon: PhoneArrowUpRightIcon, roles: ['admin', 'manager'] },
  { name: 'Reports', href: '/reports', icon: ChartBarIcon, roles: ['admin', 'manager'] },
  { name: 'Audit Logs', href: '/audit-logs', icon: ClipboardDocumentListIcon, roles: ['admin'] },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon, roles: ['admin', 'manager'] },
]

interface SidebarProps {
  mobile?: boolean
  onClose?: () => void
}

export default function Sidebar({ mobile = false, onClose }: SidebarProps) {
  const { sidebarOpen, toggleSidebar } = useUIStore()
  const { user } = useAuthStore()

  const isExpanded = mobile || sidebarOpen

  const navigation = allNavigation.filter(item => {
    if (!item.roles) return true
    return user && item.roles.includes(user.role)
  })

  const handleNavClick = () => {
    if (mobile && onClose) {
      onClose()
    }
  }

  return (
    <div
      className={clsx(
        'flex flex-col bg-white/80 backdrop-blur-xl border-r border-light-200/60 h-full',
        'transition-all duration-300 ease-snappy',
        mobile
          ? 'w-64'
          : sidebarOpen
          ? 'fixed inset-y-0 left-0 z-50 w-64'
          : 'fixed inset-y-0 left-0 z-50 w-20'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-light-200/60">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="relative flex-shrink-0">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center shadow-lg shadow-primary-500/20 transition-transform duration-300 hover:scale-105">
              <SparklesIcon className="w-5 h-5 text-white" />
            </div>
            <div className="absolute -inset-1 rounded-xl bg-primary-500/10 blur-sm -z-10" />
          </div>
          <span
            className={clsx(
              'text-lg font-bold text-light-900 whitespace-nowrap',
              'transition-all duration-300 ease-snappy',
              isExpanded ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-2 w-0'
            )}
          >
            CollectIQ
          </span>
        </div>
        {!mobile && (
          <button
            onClick={toggleSidebar}
            className={clsx(
              'rounded-lg p-2 text-light-400 hover:text-light-700 hover:bg-light-100',
              'transition-all duration-200 ease-snappy',
              'active:scale-95',
              !isExpanded && 'absolute right-1/2 translate-x-1/2'
            )}
          >
            {sidebarOpen ? (
              <ChevronLeftIcon className="h-4 w-4" />
            ) : (
              <ChevronRightIcon className="h-4 w-4" />
            )}
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto scrollbar-thin">
        {navigation.map((item, index) => (
          <NavLink
            key={item.name}
            to={item.href}
            onClick={handleNavClick}
            className={({ isActive }) =>
              clsx(
                'group flex items-center rounded-xl px-3 py-2.5 text-sm font-medium',
                'transition-all duration-200 ease-snappy',
                'relative overflow-hidden',
                isActive
                  ? 'bg-primary-50/80 text-primary-700 border-l-2 border-primary-500 -ml-px pl-[11px] shadow-[inset_0_0_16px_rgba(6,182,212,0.08)]'
                  : 'text-light-600 hover:bg-light-100/80 hover:text-light-900',
                !isExpanded && 'justify-center'
              )
            }
            style={{ animationDelay: `${index * 0.02}s` }}
          >
            {({ isActive }) => (
              <>
                {/* Hover background effect */}
                <div className={clsx(
                  'absolute inset-0 bg-gradient-to-r from-primary-500/10 to-transparent',
                  'opacity-0 group-hover:opacity-100 transition-opacity duration-200',
                  isActive && 'opacity-100'
                )} />

                <item.icon
                  className={clsx(
                    'h-5 w-5 flex-shrink-0 relative',
                    'transition-all duration-200 ease-snappy',
                    isActive
                      ? 'text-primary-600'
                      : 'text-light-400 group-hover:text-light-600',
                    isExpanded && 'mr-3',
                    'group-hover:scale-110'
                  )}
                />
                <span
                  className={clsx(
                    'relative whitespace-nowrap',
                    'transition-all duration-200 ease-snappy',
                    isExpanded
                      ? 'opacity-100 translate-x-0'
                      : 'opacity-0 translate-x-2 w-0 overflow-hidden'
                  )}
                >
                  {item.name}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* AI Status */}
      <div
        className={clsx(
          'border-t border-light-200/60 p-4',
          'transition-all duration-300 ease-snappy',
          !isExpanded && 'p-2'
        )}
      >
        <div
          className={clsx(
            'flex items-center rounded-xl bg-light-50/80 border border-light-200/60',
            'transition-all duration-300 ease-snappy',
            isExpanded ? 'gap-3 px-3 py-2.5' : 'justify-center p-2.5'
          )}
        >
          <div className="relative flex-shrink-0">
            <div className="w-2 h-2 rounded-full bg-accent-500" />
            <div className="absolute inset-0 rounded-full bg-accent-500 animate-ping opacity-50" />
          </div>
          <div
            className={clsx(
              'flex-1 min-w-0',
              'transition-all duration-300 ease-snappy',
              isExpanded ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'
            )}
          >
            <p className="text-xs font-medium text-light-700">AI Engine</p>
            <p className="text-xs text-light-500">Online</p>
          </div>
        </div>
      </div>
    </div>
  )
}
