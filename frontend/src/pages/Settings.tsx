import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  UserCircleIcon,
  BuildingOfficeIcon,
  ShieldCheckIcon,
  BellIcon,
  DocumentTextIcon,
  PencilIcon,
  TrashIcon,
  PlusIcon,
  UsersIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import api from '../services/api'
import { useAuthStore } from '../stores/authStore'
import { useChangePassword } from '../hooks/useAuth'
import Card, { CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'

// Password validation helper
const validatePassword = (password: string): { valid: boolean; errors: string[] } => {
  const errors: string[] = []
  if (password.length < 8) {
    errors.push('At least 8 characters')
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('One uppercase letter')
  }
  if (!/[@!_\-$#]/.test(password)) {
    errors.push('One special character (@, !, _, -, $, #)')
  }
  return { valid: errors.length === 0, errors }
}

function PasswordRequirements({ password }: { password: string }) {
  const hasMinLength = password.length >= 8
  const hasUppercase = /[A-Z]/.test(password)
  const hasSpecial = /[@!_\-$#]/.test(password)

  if (!password) return null

  return (
    <div className="mt-2 space-y-1">
      <p className={`text-xs flex items-center gap-1 ${hasMinLength ? 'text-green-600' : 'text-gray-500'}`}>
        {hasMinLength ? '✓' : '○'} At least 8 characters
      </p>
      <p className={`text-xs flex items-center gap-1 ${hasUppercase ? 'text-green-600' : 'text-gray-500'}`}>
        {hasUppercase ? '✓' : '○'} One uppercase letter
      </p>
      <p className={`text-xs flex items-center gap-1 ${hasSpecial ? 'text-green-600' : 'text-gray-500'}`}>
        {hasSpecial ? '✓' : '○'} One special character (@, !, _, -, $, #)
      </p>
    </div>
  )
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState('profile')
  const user = useAuthStore((state) => state.user)

  const { data: organization } = useQuery({
    queryKey: ['organization'],
    queryFn: async () => {
      const response = await api.get('/organizations/current')
      return response.data
    },
  })

  const tabs = [
    { id: 'profile', name: 'Profile', icon: UserCircleIcon },
    { id: 'organization', name: 'Organization', icon: BuildingOfficeIcon },
    { id: 'team', name: 'Team', icon: UsersIcon, adminOnly: true },
    { id: 'templates', name: 'Templates', icon: DocumentTextIcon },
    { id: 'security', name: 'Security', icon: ShieldCheckIcon },
    { id: 'notifications', name: 'Notifications', icon: BellIcon },
  ]

  // Filter tabs based on user role
  const visibleTabs = tabs.filter(tab => {
    if (tab.adminOnly && user?.role !== 'admin') return false
    return true
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-dark-100">Settings</h1>
        <p className="mt-1 text-sm text-dark-400">
          Manage your account and organization settings
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-dark-700/50">
        <nav className="-mb-px flex space-x-6 overflow-x-auto">
          {visibleTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-400'
                  : 'border-transparent text-dark-400 hover:text-dark-200 hover:border-dark-600'
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && <ProfileSettings />}

      {/* Organization Tab */}
      {activeTab === 'organization' && organization && (
        <OrganizationSettings organization={organization} />
      )}

      {/* Team Tab */}
      {activeTab === 'team' && user?.role === 'admin' && <TeamSettings />}

      {/* Templates Tab */}
      {activeTab === 'templates' && <TemplatesSettings />}

      {/* Security Tab */}
      {activeTab === 'security' && <SecuritySettings />}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && <NotificationSettings />}
    </div>
  )
}

function ProfileSettings() {
  const user = useAuthStore((state) => state.user)
  const updateUser = useAuthStore((state) => state.updateUser)

  const { register, handleSubmit } = useForm({
    defaultValues: {
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      phone: '',
    },
  })

  const updateProfile = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.put('/users/me', data)
      return response.data
    },
    onSuccess: (data) => {
      updateUser(data)
      toast.success('Profile updated successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update profile')
    },
  })

  const onSubmit = (data: any) => {
    updateProfile.mutate(data)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile Information</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 max-w-lg">
        <Input
          id="email"
          label="Email"
          value={user?.email}
          disabled
          helperText="Email cannot be changed"
        />
        <Input
          id="first_name"
          label="First Name"
          placeholder="Enter your first name"
          {...register('first_name')}
        />
        <Input
          id="last_name"
          label="Last Name"
          placeholder="Enter your last name"
          {...register('last_name')}
        />
        <Input
          id="phone"
          label="Phone"
          placeholder="+91 98765 43210"
          {...register('phone')}
        />
        <Button type="submit" loading={updateProfile.isPending}>Save Changes</Button>
      </form>
    </Card>
  )
}

function OrganizationSettings({ organization }: { organization: any }) {
  const queryClient = useQueryClient()
  const { register, handleSubmit } = useForm({
    defaultValues: {
      name: organization.name || '',
      email: organization.email || '',
      phone: organization.phone || '',
      address_line1: organization.address_line1 || '',
      city: organization.city || '',
      state: organization.state || '',
      pincode: organization.pincode || '',
      gstin: organization.gstin || '',
    },
  })

  const updateOrg = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.put('/organizations/current', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization'] })
      toast.success('Organization updated successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update organization')
    },
  })

  const onSubmit = (data: any) => {
    updateOrg.mutate(data)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Organization Details</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 max-w-lg">
        <Input
          id="org_name"
          label="Organization Name"
          placeholder="Company name"
          {...register('name')}
        />
        <Input
          id="org_email"
          label="Email"
          type="email"
          placeholder="contact@company.com"
          {...register('email')}
        />
        <Input
          id="org_phone"
          label="Phone"
          placeholder="+91 22 1234 5678"
          {...register('phone')}
        />
        <Input
          id="address"
          label="Address"
          placeholder="Street address"
          {...register('address_line1')}
        />
        <div className="grid grid-cols-3 gap-4">
          <Input
            id="city"
            label="City"
            placeholder="Mumbai"
            {...register('city')}
          />
          <Input
            id="state"
            label="State"
            placeholder="Maharashtra"
            {...register('state')}
          />
          <Input
            id="pincode"
            label="Pincode"
            placeholder="400001"
            {...register('pincode')}
          />
        </div>
        <Input
          id="gstin"
          label="GSTIN"
          placeholder="22AAAAA0000A1Z5"
          {...register('gstin')}
        />
        <Button type="submit" loading={updateOrg.isPending}>Save Changes</Button>
      </form>
    </Card>
  )
}

function SecuritySettings() {
  const changePassword = useChangePassword()
  const { register, handleSubmit, reset, watch } = useForm({
    defaultValues: {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    },
  })

  const newPasswordValue = watch('newPassword')
  const passwordValidation = newPasswordValue ? validatePassword(newPasswordValue) : { valid: true, errors: [] }

  const onSubmit = (data: any) => {
    if (data.newPassword !== data.confirmPassword) {
      toast.error('Passwords do not match')
      return
    }
    const validation = validatePassword(data.newPassword)
    if (!validation.valid) {
      toast.error('Password does not meet requirements')
      return
    }
    changePassword.mutate(
      {
        currentPassword: data.currentPassword,
        newPassword: data.newPassword,
      },
      {
        onSuccess: () => reset(),
      }
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change Password</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 max-w-lg">
        <Input
          id="currentPassword"
          type="password"
          label="Current Password"
          placeholder="Enter current password"
          {...register('currentPassword', { required: true })}
        />
        <div>
          <Input
            id="newPassword"
            type="password"
            label="New Password"
            placeholder="Enter new password"
            {...register('newPassword', { required: true })}
          />
          <PasswordRequirements password={newPasswordValue || ''} />
        </div>
        <Input
          id="confirmPassword"
          type="password"
          label="Confirm New Password"
          placeholder="Confirm new password"
          {...register('confirmPassword', { required: true })}
        />
        <Button
          type="submit"
          loading={changePassword.isPending}
          disabled={!!newPasswordValue && !passwordValidation.valid}
        >
          Change Password
        </Button>
      </form>
    </Card>
  )
}

function NotificationSettings() {
  const [preferences, setPreferences] = useState({
    emailNotifications: true,
    dailyReports: true,
    campaignAlerts: true,
    aiInsights: true,
  })

  const handleToggle = (key: keyof typeof preferences) => {
    setPreferences((prev) => {
      const newPrefs = { ...prev, [key]: !prev[key] }
      // In a real app, this would save to the backend
      toast.success(`${key.replace(/([A-Z])/g, ' $1').trim()} ${newPrefs[key] ? 'enabled' : 'disabled'}`)
      return newPrefs
    })
  }

  const notificationItems = [
    {
      key: 'emailNotifications' as const,
      title: 'Email Notifications',
      description: 'Receive email updates about your cases',
    },
    {
      key: 'dailyReports' as const,
      title: 'Daily Reports',
      description: 'Receive daily summary reports',
    },
    {
      key: 'campaignAlerts' as const,
      title: 'Campaign Alerts',
      description: 'Get notified when campaigns complete',
    },
    {
      key: 'aiInsights' as const,
      title: 'AI Insights',
      description: 'Receive AI-generated recommendations',
    },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notification Preferences</CardTitle>
      </CardHeader>
      <div className="space-y-5">
        {notificationItems.map((item) => (
          <div key={item.key} className="flex items-center justify-between py-2">
            <div>
              <div className="font-medium text-light-900">{item.title}</div>
              <div className="text-sm text-light-500">{item.description}</div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={preferences[item.key]}
                onChange={() => handleToggle(item.key)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-light-300 peer-focus:ring-2 peer-focus:ring-primary-500/20 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-500 peer-checked:after:bg-white shadow-inner" />
            </label>
          </div>
        ))}
      </div>
    </Card>
  )
}

interface Template {
  id: string
  name: string
  channel: string
  language: string
  content: string
  category: string
  whatsapp_template_id?: string
  is_active: boolean
  is_default: boolean
}

function TemplatesSettings() {
  const queryClient = useQueryClient()
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [filterChannel, setFilterChannel] = useState<string>('')

  const { data: templates, isLoading } = useQuery({
    queryKey: ['templates', filterChannel],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filterChannel) params.append('channel', filterChannel)
      params.append('active_only', 'false')
      const response = await api.get(`/templates?${params.toString()}`)
      return response.data as Template[]
    },
  })

  const createTemplate = useMutation({
    mutationFn: async (data: Partial<Template>) => {
      const response = await api.post('/templates', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      toast.success('Template created')
      setIsCreating(false)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create template')
    },
  })

  const updateTemplate = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Template> }) => {
      const response = await api.put(`/templates/${id}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      toast.success('Template updated')
      setEditingTemplate(null)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update template')
    },
  })

  const deleteTemplate = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/templates/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      toast.success('Template deleted')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete template')
    },
  })

  const seedDefaults = useMutation({
    mutationFn: async () => {
      const response = await api.post('/templates/seed-defaults')
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      if (data.status === 'seeded') {
        toast.success(`Seeded ${data.count} default templates`)
      } else {
        toast.success('Templates already exist')
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to seed templates')
    },
  })

  const groupedTemplates = templates?.reduce((acc, template) => {
    const key = `${template.channel}-${template.language}`
    if (!acc[key]) acc[key] = []
    acc[key].push(template)
    return acc
  }, {} as Record<string, Template[]>) || {}

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Message Templates</CardTitle>
              <p className="text-sm text-dark-400 mt-1">
                Pre-approved templates for SMS and WhatsApp messages
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => seedDefaults.mutate()}
                loading={seedDefaults.isPending}
              >
                Seed Defaults
              </Button>
              <Button
                size="sm"
                onClick={() => setIsCreating(true)}
              >
                <PlusIcon className="h-4 w-4 mr-1" />
                Add Template
              </Button>
            </div>
          </div>
        </CardHeader>

        {/* Filter */}
        <div className="mb-4">
          <select
            value={filterChannel}
            onChange={(e) => setFilterChannel(e.target.value)}
            className="px-3 py-2 bg-dark-700/50 border border-dark-600 rounded-lg text-dark-100 text-sm"
          >
            <option value="">All Channels</option>
            <option value="sms">SMS</option>
            <option value="whatsapp">WhatsApp</option>
          </select>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-dark-400">Loading templates...</div>
        ) : Object.keys(groupedTemplates).length === 0 ? (
          <div className="text-center py-8">
            <p className="text-dark-400">No templates found</p>
            <p className="text-sm text-dark-500 mt-1">Click "Seed Defaults" to add default templates</p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedTemplates).map(([key, templateGroup]) => {
              const [channel, language] = key.split('-')
              return (
                <div key={key}>
                  <h3 className="text-sm font-medium text-dark-300 mb-3 uppercase tracking-wide">
                    {channel === 'sms' ? 'SMS' : 'WhatsApp'} - {language === 'en' ? 'English' : language === 'hinglish' ? 'Hinglish' : language === 'hi' ? 'Hindi' : language}
                  </h3>
                  <div className="space-y-2">
                    {templateGroup.map((template) => (
                      <div
                        key={template.id}
                        className={`p-4 rounded-lg border ${
                          template.is_active
                            ? 'bg-dark-800/50 border-dark-700'
                            : 'bg-dark-900/50 border-dark-800 opacity-60'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-dark-100">{template.name}</span>
                              <span className="px-2 py-0.5 text-xs rounded-full bg-dark-700 text-dark-300">
                                {template.category.replace('_', ' ')}
                              </span>
                              {template.is_default && (
                                <span className="px-2 py-0.5 text-xs rounded-full bg-primary-500/20 text-primary-400">
                                  Default
                                </span>
                              )}
                              {!template.is_active && (
                                <span className="px-2 py-0.5 text-xs rounded-full bg-red-500/20 text-red-400">
                                  Inactive
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-dark-400 mt-1 font-mono">{template.content}</p>
                            {template.whatsapp_template_id && (
                              <p className="text-xs text-dark-500 mt-1">
                                WhatsApp ID: {template.whatsapp_template_id}
                              </p>
                            )}
                          </div>
                          <div className="flex gap-1 ml-4">
                            <button
                              onClick={() => setEditingTemplate(template)}
                              className="p-1.5 text-dark-400 hover:text-dark-200 hover:bg-dark-700 rounded"
                            >
                              <PencilIcon className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => {
                                if (confirm('Delete this template?')) {
                                  deleteTemplate.mutate(template.id)
                                }
                              }}
                              className="p-1.5 text-dark-400 hover:text-red-400 hover:bg-dark-700 rounded"
                            >
                              <TrashIcon className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      {/* Create/Edit Modal */}
      {(isCreating || editingTemplate) && (
        <TemplateModal
          template={editingTemplate}
          onClose={() => {
            setIsCreating(false)
            setEditingTemplate(null)
          }}
          onSave={(data) => {
            if (editingTemplate) {
              updateTemplate.mutate({ id: editingTemplate.id, data })
            } else {
              createTemplate.mutate(data)
            }
          }}
          isLoading={createTemplate.isPending || updateTemplate.isPending}
        />
      )}
    </div>
  )
}

// ==================== Team Settings ====================

interface TeamMember {
  id: string
  email: string
  first_name: string
  last_name: string | null
  role: string
  is_active: boolean
  avatar_url: string | null
}

function TeamSettings() {
  const queryClient = useQueryClient()
  const [isCreating, setIsCreating] = useState(false)
  const [editingMember, setEditingMember] = useState<TeamMember | null>(null)
  const [filterRole, setFilterRole] = useState<string>('')

  const { data: members, isLoading } = useQuery({
    queryKey: ['teamMembers', filterRole],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filterRole) params.append('role', filterRole)
      const response = await api.get(`/users?${params.toString()}`)
      return response.data.items as TeamMember[]
    },
  })

  const createUser = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.post('/users', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamMembers'] })
      toast.success('Team member added successfully')
      setIsCreating(false)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to add team member')
    },
  })

  const updateUser = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => {
      const response = await api.put(`/users/${id}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamMembers'] })
      toast.success('Team member updated')
      setEditingMember(null)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update team member')
    },
  })

  const deactivateUser = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/users/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamMembers'] })
      toast.success('Team member deactivated')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to deactivate team member')
    },
  })

  const reactivateUser = useMutation({
    mutationFn: async (id: string) => {
      const response = await api.put(`/users/${id}`, { is_active: true })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teamMembers'] })
      toast.success('Team member reactivated')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to reactivate team member')
    },
  })

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin': return 'bg-red-100 text-red-700 border-red-200'
      case 'manager': return 'bg-blue-100 text-blue-700 border-blue-200'
      case 'agent': return 'bg-green-100 text-green-700 border-green-200'
      case 'viewer': return 'bg-gray-100 text-gray-700 border-gray-200'
      default: return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Team Members</CardTitle>
              <p className="text-sm text-gray-500 mt-1">
                Manage users in your organization
              </p>
            </div>
            <Button size="sm" onClick={() => setIsCreating(true)}>
              <PlusIcon className="h-4 w-4 mr-1" />
              Add Member
            </Button>
          </div>
        </CardHeader>

        {/* Filter */}
        <div className="mb-4">
          <select
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value)}
            className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 text-sm"
          >
            <option value="">All Roles</option>
            <option value="admin">Admin</option>
            <option value="manager">Manager</option>
            <option value="agent">Agent</option>
            <option value="viewer">Viewer</option>
          </select>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-gray-400">Loading team members...</div>
        ) : members?.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-400">No team members found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Name</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Email</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Role</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {members?.map((member) => (
                  <tr key={member.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white text-sm font-medium">
                          {member.first_name[0]}{member.last_name?.[0] || ''}
                        </div>
                        <span className="font-medium text-gray-900">
                          {member.first_name} {member.last_name || ''}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">{member.email}</td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRoleBadgeColor(member.role)}`}>
                        {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {member.is_active ? (
                        <span className="inline-flex items-center gap-1 text-green-600 text-sm">
                          <CheckCircleIcon className="h-4 w-4" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-gray-400 text-sm">
                          <XCircleIcon className="h-4 w-4" />
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex justify-end gap-1">
                        <button
                          onClick={() => setEditingMember(member)}
                          className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
                          title="Edit"
                        >
                          <PencilIcon className="h-4 w-4" />
                        </button>
                        {member.is_active ? (
                          <button
                            onClick={() => {
                              if (confirm(`Deactivate ${member.first_name}? They will no longer be able to log in.`)) {
                                deactivateUser.mutate(member.id)
                              }
                            }}
                            className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                            title="Deactivate"
                          >
                            <XCircleIcon className="h-4 w-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => reactivateUser.mutate(member.id)}
                            className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded"
                            title="Reactivate"
                          >
                            <CheckCircleIcon className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Role Descriptions */}
      <Card>
        <CardHeader>
          <CardTitle>Role Permissions</CardTitle>
        </CardHeader>
        <div className="space-y-4">
          <div className="flex gap-4 items-start p-3 rounded-lg bg-gray-50">
            <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRoleBadgeColor('admin')}`}>
              Admin
            </span>
            <p className="text-sm text-gray-600">Full access to all features, settings, and user management</p>
          </div>
          <div className="flex gap-4 items-start p-3 rounded-lg bg-gray-50">
            <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRoleBadgeColor('manager')}`}>
              Manager
            </span>
            <p className="text-sm text-gray-600">Access to all cases, reports, campaigns, and can assign cases to agents</p>
          </div>
          <div className="flex gap-4 items-start p-3 rounded-lg bg-gray-50">
            <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRoleBadgeColor('agent')}`}>
              Agent
            </span>
            <p className="text-sm text-gray-600">Can only see and work on cases assigned to them</p>
          </div>
          <div className="flex gap-4 items-start p-3 rounded-lg bg-gray-50">
            <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRoleBadgeColor('viewer')}`}>
              Viewer
            </span>
            <p className="text-sm text-gray-600">Read-only access to assigned cases, cannot make calls or changes</p>
          </div>
        </div>
      </Card>

      {/* Create/Edit Modal */}
      {(isCreating || editingMember) && (
        <TeamMemberModal
          member={editingMember}
          onClose={() => {
            setIsCreating(false)
            setEditingMember(null)
          }}
          onSave={(data) => {
            if (editingMember) {
              updateUser.mutate({ id: editingMember.id, data })
            } else {
              createUser.mutate(data)
            }
          }}
          isLoading={createUser.isPending || updateUser.isPending}
        />
      )}
    </div>
  )
}

function TeamMemberModal({
  member,
  onClose,
  onSave,
  isLoading,
}: {
  member: TeamMember | null
  onClose: () => void
  onSave: (data: any) => void
  isLoading: boolean
}) {
  const [showPasswordReset, setShowPasswordReset] = useState(false)
  const { register, handleSubmit, formState: { errors }, watch } = useForm({
    defaultValues: {
      email: member?.email || '',
      first_name: member?.first_name || '',
      last_name: member?.last_name || '',
      role: member?.role || 'agent',
      password: '',
    },
  })

  const passwordValue = watch('password')
  const passwordValidation = passwordValue ? validatePassword(passwordValue) : { valid: true, errors: [] }

  const onSubmit = (data: any) => {
    // Validate password if provided
    if (data.password) {
      const validation = validatePassword(data.password)
      if (!validation.valid) {
        toast.error('Password does not meet requirements')
        return
      }
    } else {
      delete data.password
    }
    // Remove email if editing (can't change email)
    if (member) {
      delete data.email
    }
    onSave(data)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          {member ? 'Edit Team Member' : 'Add Team Member'}
        </h2>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            id="email"
            label="Email"
            type="email"
            placeholder="user@example.com"
            disabled={!!member}
            {...register('email', { required: !member })}
            error={errors.email ? 'Email is required' : undefined}
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              id="first_name"
              label="First Name"
              placeholder="John"
              {...register('first_name', { required: true })}
              error={errors.first_name ? 'Required' : undefined}
            />
            <Input
              id="last_name"
              label="Last Name"
              placeholder="Doe"
              {...register('last_name')}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Role</label>
            <select
              {...register('role', { required: true })}
              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
            >
              <option value="agent">Agent</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
              <option value="viewer">Viewer</option>
            </select>
            <p className="mt-1 text-xs text-gray-500">
              {member ? 'Change the role for this user' : 'Select a role for the new user'}
            </p>
          </div>

          {/* Password section */}
          {!member ? (
            <div>
              <Input
                id="password"
                label="Password"
                type="password"
                placeholder="Enter a strong password"
                {...register('password', { required: true })}
                error={errors.password && !passwordValue ? 'Password is required' : undefined}
              />
              <PasswordRequirements password={passwordValue || ''} />
            </div>
          ) : (
            <div className="space-y-3">
              {!showPasswordReset ? (
                <button
                  type="button"
                  onClick={() => setShowPasswordReset(true)}
                  className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                >
                  Reset Password
                </button>
              ) : (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="block text-sm font-medium text-amber-800">New Password</label>
                    <button
                      type="button"
                      onClick={() => setShowPasswordReset(false)}
                      className="text-xs text-amber-600 hover:text-amber-700"
                    >
                      Cancel
                    </button>
                  </div>
                  <input
                    type="password"
                    placeholder="Enter new password"
                    {...register('password')}
                    className="w-full px-3 py-2 bg-white border border-amber-300 rounded-lg text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500"
                  />
                  <PasswordRequirements password={passwordValue || ''} />
                  <p className="text-xs text-amber-700">
                    The user will need to use this new password to log in.
                  </p>
                </div>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button
              type="submit"
              loading={isLoading}
              className="flex-1"
              disabled={!member && !!passwordValue && !passwordValidation.valid}
            >
              {member ? 'Update' : 'Add Member'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

function TemplateModal({
  template,
  onClose,
  onSave,
  isLoading,
}: {
  template: Template | null
  onClose: () => void
  onSave: (data: Partial<Template>) => void
  isLoading: boolean
}) {
  const { register, handleSubmit } = useForm({
    defaultValues: {
      name: template?.name || '',
      channel: template?.channel || 'sms',
      language: template?.language || 'en',
      content: template?.content || '',
      category: template?.category || 'payment_reminder',
      whatsapp_template_id: template?.whatsapp_template_id || '',
      is_active: template?.is_active ?? true,
      is_default: template?.is_default ?? false,
    },
  })

  const onSubmit = (data: any) => {
    onSave({
      ...data,
      whatsapp_template_id: data.whatsapp_template_id || undefined,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          {template ? 'Edit Template' : 'Create Template'}
        </h2>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            id="name"
            label="Template Name"
            placeholder="e.g., Payment Reminder - EN"
            {...register('name', { required: true })}
          />

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Channel</label>
              <select
                {...register('channel')}
                className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                disabled={!!template}
              >
                <option value="sms">SMS</option>
                <option value="whatsapp">WhatsApp</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Language</label>
              <select
                {...register('language')}
                className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                disabled={!!template}
              >
                <option value="en">English</option>
                <option value="hinglish">Hinglish</option>
                <option value="hi">Hindi</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Category</label>
            <select
              {...register('category')}
              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
            >
              <option value="payment_reminder">Payment Reminder</option>
              <option value="overdue_notice">Overdue Notice</option>
              <option value="follow_up">Follow Up</option>
              <option value="payment_confirmation">Payment Confirmation</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Content
              <span className="text-gray-500 font-normal ml-2">
                Placeholders: {'{name}'}, {'{amount}'}, {'{dpd}'}, {'{emi}'}, {'{due_date}'}
              </span>
            </label>
            <textarea
              {...register('content', { required: true })}
              rows={3}
              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 font-mono text-sm"
              placeholder="Hi {name}, your EMI of Rs.{emi} is due..."
            />
          </div>

          <Input
            id="whatsapp_template_id"
            label="WhatsApp Template ID (optional)"
            placeholder="Meta-approved template ID"
            {...register('whatsapp_template_id')}
          />

          <div className="flex gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                {...register('is_active')}
                className="rounded border-gray-300 bg-white text-primary-500"
              />
              <span className="text-sm text-gray-700">Active</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                {...register('is_default')}
                className="rounded border-gray-300 bg-white text-primary-500"
              />
              <span className="text-sm text-gray-700">Default for category</span>
            </label>
          </div>

          <div className="flex gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button type="submit" loading={isLoading} className="flex-1">
              {template ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
