import { Fragment, useState } from 'react'
import { Menu, Popover, Transition } from '@headlessui/react'
import {
  BellIcon,
  MagnifyingGlassIcon,
  Bars3Icon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { useAuthStore } from '../../stores/authStore'
import { useUIStore } from '../../stores/uiStore'
import { useLogout } from '../../hooks/useAuth'
import clsx from 'clsx'

// Mock notifications - in real app these would come from an API
const mockNotifications = [
  { id: 1, type: 'success', title: 'Campaign Completed', message: 'Voice campaign "Q4 Collection" finished', time: '5 min ago' },
  { id: 2, type: 'warning', title: 'High Priority Case', message: 'Case #CS-2024-0451 needs attention', time: '1 hour ago' },
  { id: 3, type: 'info', title: 'New AI Insight', message: 'Best time to call borrower identified', time: '2 hours ago' },
]

export default function Header() {
  const user = useAuthStore((state) => state.user)
  const { setMobileSidebarOpen } = useUIStore()
  const logout = useLogout()
  const [searchOpen, setSearchOpen] = useState(false)

  return (
    <header className="sticky top-0 z-40 flex h-14 sm:h-16 shrink-0 items-center gap-x-2 sm:gap-x-4 border-b border-light-200 bg-white/80 backdrop-blur-xl px-3 sm:px-4 lg:px-8 shadow-sm">
      {/* Mobile menu button */}
      <button
        type="button"
        className="lg:hidden -m-2.5 p-2.5 text-light-500 hover:text-light-700"
        onClick={() => setMobileSidebarOpen(true)}
      >
        <span className="sr-only">Open sidebar</span>
        <Bars3Icon className="h-6 w-6" aria-hidden="true" />
      </button>

      {/* Divider on mobile */}
      <div className="h-6 w-px bg-light-200 lg:hidden" />

      <div className="flex flex-1 gap-x-2 sm:gap-x-4 self-stretch lg:gap-x-6">
        {/* Search - Desktop */}
        <div className="hidden sm:flex flex-1 items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <MagnifyingGlassIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-light-400" />
            <input
              type="search"
              placeholder="Search cases, borrowers..."
              className="w-full rounded-lg bg-light-50 border border-light-200 py-2 pl-10 pr-4 text-sm text-light-900 placeholder-light-400 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/20 transition-colors"
            />
          </div>
        </div>

        {/* Mobile search toggle */}
        <div className="flex flex-1 items-center sm:hidden">
          {searchOpen ? (
            <div className="flex items-center gap-2 w-full">
              <input
                type="search"
                placeholder="Search..."
                autoFocus
                className="flex-1 rounded-lg bg-light-50 border border-light-200 py-1.5 px-3 text-sm text-light-900 placeholder-light-400 focus:outline-none focus:border-primary-500"
              />
              <button
                onClick={() => setSearchOpen(false)}
                className="p-1.5 text-light-500"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setSearchOpen(true)}
              className="p-1.5 text-light-500 hover:text-light-700"
            >
              <MagnifyingGlassIcon className="h-5 w-5" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-x-2 sm:gap-x-3 lg:gap-x-4">
          {/* Notifications */}
          <Popover className="relative">
            <Popover.Button className="relative rounded-lg p-1.5 sm:p-2 text-light-500 hover:text-light-700 hover:bg-light-100 transition-colors focus:outline-none">
              <BellIcon className="h-5 w-5" />
              <span className="absolute right-1 top-1 sm:right-1.5 sm:top-1.5 flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-500" />
              </span>
            </Popover.Button>
            <Transition
              as={Fragment}
              enter="transition ease-out duration-200"
              enterFrom="opacity-0 translate-y-1"
              enterTo="opacity-100 translate-y-0"
              leave="transition ease-in duration-150"
              leaveFrom="opacity-100 translate-y-0"
              leaveTo="opacity-0 translate-y-1"
            >
              <Popover.Panel className="absolute right-0 z-10 mt-2 w-80 origin-top-right rounded-xl bg-white border border-light-200 shadow-lg focus:outline-none">
                <div className="px-4 py-3 border-b border-light-200">
                  <p className="text-sm font-semibold text-light-900">Notifications</p>
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {mockNotifications.map((notification) => (
                    <div key={notification.id} className="px-4 py-3 hover:bg-light-50 cursor-pointer border-b border-light-100 last:border-0">
                      <div className="flex gap-3">
                        <div className="flex-shrink-0">
                          {notification.type === 'success' && <CheckCircleIcon className="h-5 w-5 text-accent-500" />}
                          {notification.type === 'warning' && <ExclamationCircleIcon className="h-5 w-5 text-amber-500" />}
                          {notification.type === 'info' && <InformationCircleIcon className="h-5 w-5 text-primary-500" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-light-900">{notification.title}</p>
                          <p className="text-sm text-light-500 truncate">{notification.message}</p>
                          <p className="text-xs text-light-400 mt-1">{notification.time}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="px-4 py-3 border-t border-light-200">
                  <a href="/settings?tab=notifications" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
                    View all notifications
                  </a>
                </div>
              </Popover.Panel>
            </Transition>
          </Popover>

          {/* Divider */}
          <div className="hidden sm:block h-6 w-px bg-light-200" />

          {/* Profile dropdown */}
          <Menu as="div" className="relative">
            <Menu.Button className="flex items-center gap-x-2 sm:gap-x-3 rounded-lg p-1 sm:p-1.5 text-sm hover:bg-light-100 transition-colors">
              <div className="h-7 w-7 sm:h-8 sm:w-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center shadow-sm">
                <span className="text-xs sm:text-sm font-semibold text-white">
                  {user?.first_name?.[0]}{user?.last_name?.[0]}
                </span>
              </div>
              <span className="hidden md:flex md:flex-col md:items-start">
                <span className="text-sm font-medium text-light-900">
                  {user?.first_name} {user?.last_name}
                </span>
                <span className="text-xs text-light-500 capitalize">{user?.role}</span>
              </span>
            </Menu.Button>

            <Transition
              as={Fragment}
              enter="transition ease-out duration-100"
              enterFrom="transform opacity-0 scale-95"
              enterTo="transform opacity-100 scale-100"
              leave="transition ease-in duration-75"
              leaveFrom="transform opacity-100 scale-100"
              leaveTo="transform opacity-0 scale-95"
            >
              <Menu.Items className="absolute right-0 z-10 mt-2 w-56 origin-top-right rounded-xl bg-white border border-light-200 py-2 shadow-lg focus:outline-none">
                <div className="px-4 py-2 border-b border-light-200">
                  <p className="text-sm font-medium text-light-900">{user?.first_name} {user?.last_name}</p>
                  <p className="text-xs text-light-500 truncate">{user?.email}</p>
                </div>
                {/* Only show Settings for admin/manager */}
                {user?.role && ['admin', 'manager'].includes(user.role) && (
                  <div className="py-1">
                    <Menu.Item>
                      {({ active }) => (
                        <a
                          href="/settings"
                          className={clsx(
                            'flex items-center gap-2 px-4 py-2 text-sm transition-colors',
                            active ? 'bg-light-50 text-light-900' : 'text-light-700'
                          )}
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          </svg>
                          Settings
                        </a>
                      )}
                    </Menu.Item>
                  </div>
                )}
                <div className="border-t border-light-200 py-1">
                  <Menu.Item>
                    {({ active }) => (
                      <button
                        onClick={logout}
                        className={clsx(
                          'flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition-colors',
                          active ? 'bg-light-50 text-red-600' : 'text-light-700'
                        )}
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
                        </svg>
                        Sign out
                      </button>
                    )}
                  </Menu.Item>
                </div>
              </Menu.Items>
            </Transition>
          </Menu>
        </div>
      </div>
    </header>
  )
}
