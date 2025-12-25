export interface User {
  id: string
  email: string
  first_name: string
  last_name: string | null
  role: string
  organization_id: string
  organization_name: string
  is_active: boolean
  avatar_url: string | null
}

export interface Borrower {
  id: string
  external_id: string | null
  first_name: string
  last_name: string | null
  primary_phone: string
  secondary_phone: string | null
  email: string | null
  city: string | null
  state: string | null
  tags: string[]
  is_active: boolean
}

export interface Loan {
  id: string
  external_loan_id: string | null
  loan_account_number: string | null
  loan_type: string
  principal_amount: number
  emi_amount: number
  total_outstanding: number | null
  overdue_amount: number
  dpd: number
  bucket: string | null
  status: string
  collection_status: string
  borrower_id: string
}

export interface Case {
  id: string
  case_number: string
  status: string
  priority: number
  case_type: string
  loan_id: string
  next_follow_up: string | null
  last_contact_date: string | null
  total_attempts: number
  tags: string[]
  created_at: string
}

export interface CaseWithDetails extends Case {
  borrower_id: string
  borrower_name: string
  borrower_phone: string
  loan_account_number: string | null
  total_outstanding: number | null
  dpd: number
  bucket: string | null
  assigned_agent_name: string | null
  successful_contacts: number
  ai_summary: string | null
}

export interface Communication {
  id: string
  channel: string
  direction: string
  status: string
  borrower_id: string
  from_number: string | null
  to_number: string | null
  initiated_at: string
  duration_seconds: number
  outcome: string | null
  is_ai_handled: boolean
}

export interface Campaign {
  id: string
  name: string
  campaign_type: string
  status: string
  total_targets: number
  total_attempted: number
  total_successful: number
  scheduled_start: string | null
  created_at: string
}

export interface CaseNote {
  id: string
  case_id: string
  author_id: string | null
  author_name: string | null
  content: string
  note_type: string
  is_system: boolean
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DashboardStats {
  portfolio: {
    total_outstanding: number
    total_overdue: number
    active_loans: number
    overdue_percentage: number
  }
  cases: {
    open_cases: number
    resolved_today: number
  }
  collections: {
    collected_this_month: number
  }
  communications: {
    calls_today: number
    successful_contacts_today: number
    contact_rate: number
  }
  campaigns: {
    active: number
  }
}
