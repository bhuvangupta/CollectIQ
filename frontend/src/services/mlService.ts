import api from './api'

export interface PriorityResult {
  score: number
  priority_level: number
  factors: {
    overdue_ratio: number
    days_factor: number
    risk_factor: number
    penalty_30d: boolean
  }
  calculated_at: string
}

export interface StrategyResult {
  strategy: string
  channels: string[]
  frequency: string
  tone: string
  description: string
  suggested_actions?: string[]
  consider_legal_action?: boolean
  legal_action_recommended?: boolean
}

export interface RiskResult {
  score: number
  risk_level: string
  default_probability: number
  factors: {
    dpd_factor: number
    overdue_factor: number
    contact_factor: number
    promise_factor: number
  }
  assessed_at: string
  model: string
}

export interface LoanIntelligence {
  loan_id: string
  loan_account_number: string
  dpd: number
  bucket: string
  overdue_amount: number
  risk: RiskResult
  priority: PriorityResult
  strategy: StrategyResult
}

export interface CaseRecalculateResult {
  case_id: string
  updated_priority: number
  priority_details: PriorityResult
  risk_details: RiskResult
}

export interface BatchRecalculateResult {
  status: string
  cases_updated: number
}

export const mlService = {
  // Calculate priority score
  calculatePriority: async (data: {
    overdue_amount: number
    principal_amount: number
    dpd: number
    risk_score?: number
  }): Promise<PriorityResult> => {
    const response = await api.post('/ml/priority/calculate', data)
    return response.data
  },

  // Get collection strategy recommendation
  recommendStrategy: async (data: {
    dpd: number
    risk_level?: string
  }): Promise<StrategyResult> => {
    const response = await api.post('/ml/strategy/recommend', data)
    return response.data
  },

  // Assess risk
  assessRisk: async (data: {
    dpd: number
    overdue_amount: number
    principal_amount: number
    total_attempts?: number
    promises_broken?: number
  }): Promise<RiskResult> => {
    const response = await api.post('/ml/risk/assess', data)
    return response.data
  },

  // Get full intelligence for a loan
  getLoanIntelligence: async (loanId: string): Promise<LoanIntelligence> => {
    const response = await api.get(`/ml/loans/${loanId}/intelligence`)
    return response.data
  },

  // Recalculate case priority
  recalculateCasePriority: async (caseId: string): Promise<CaseRecalculateResult> => {
    const response = await api.post(`/ml/cases/${caseId}/recalculate`)
    return response.data
  },

  // Batch recalculate all priorities
  batchRecalculatePriorities: async (): Promise<BatchRecalculateResult> => {
    const response = await api.post('/ml/batch/recalculate-priorities')
    return response.data
  },
}

export default mlService
