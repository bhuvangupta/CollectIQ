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
} from '@heroicons/react/24/outline'
import { useUIStore } from '../../stores/uiStore'
import { useAuthStore } from '../../stores/authStore'
import clsx from 'clsx'

// Define navigation with role restrictions
// roles: undefined = all roles, array = specific roles only
const allNavigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Cases', href: '/cases', icon: FolderIcon },
  { name: 'Borrowers', href: '/borrowers', icon: UsersIcon },
  { name: 'Campaigns', href: '/campaigns', icon: MegaphoneIcon, roles: ['admin', 'manager'] },
  { name: 'Communications', href: '/communications', icon: PhoneIcon },
  { name: 'Reports', href: '/reports', icon: ChartBarIcon, roles: ['admin', 'manager'] },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon, roles: ['admin', 'manager'] },
]

interface SidebarProps {
  mobile?: boolean
  onClose?: () => void
}

export default function Sidebar({ mobile = false, onClose }: SidebarProps) {
  const { sidebarOpen, toggleSidebar } = useUIStore()
  const { user } = useAuthStore()

  // In mobile mode, always show expanded
  const isExpanded = mobile || sidebarOpen

  // Filter navigation based on user role
  const navigation = allNavigation.filter(item => {
    if (!item.roles) return true // No role restriction
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
        'flex flex-col bg-white border-r border-light-200 transition-all duration-300 h-full shadow-sm',
        mobile ? 'w-64' : (sidebarOpen ? 'fixed inset-y-0 left-0 z-50 w-64' : 'fixed inset-y-0 left-0 z-50 w-20')
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-light-200">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center shadow-md">
              <SparklesIcon className="w-5 h-5 text-white" />
            </div>
            <div className="absolute -inset-1 rounded-lg bg-primary-500/10 blur-sm -z-10" />
          </div>
          {isExpanded && (
            <span className="text-lg font-bold text-light-900">
              CollectIQ
            </span>
          )}
        </div>
        {!mobile && (
          <button
            onClick={toggleSidebar}
            className="rounded-lg p-2 text-light-500 hover:bg-light-100 hover:text-light-700 transition-colors"
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
      <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            onClick={handleNavClick}
            className={({ isActive }) =>
              clsx(
                'group flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-primary-50 text-primary-700 border-l-2 border-primary-500 -ml-px pl-[11px]'
                  : 'text-light-600 hover:bg-light-100 hover:text-light-900',
                !isExpanded && 'justify-center'
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={clsx(
                    'h-5 w-5 flex-shrink-0 transition-colors',
                    isActive ? 'text-primary-600' : 'text-light-400 group-hover:text-light-600',
                    isExpanded && 'mr-3'
                  )}
                />
                {isExpanded && item.name}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* AI Status */}
      {isExpanded && (
        <div className="border-t border-light-200 p-4">
          <div className="flex items-center gap-3 rounded-lg bg-light-50 px-3 py-2.5 border border-light-200">
            <div className="relative">
              <div className="w-2 h-2 rounded-full bg-accent-500" />
              <div className="absolute inset-0 rounded-full bg-accent-500 animate-ping opacity-50" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-light-700">AI Engine</p>
              <p className="text-xs text-light-500">Online</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
