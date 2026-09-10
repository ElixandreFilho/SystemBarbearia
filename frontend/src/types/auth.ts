export type UserRole = 'ADMIN' | 'CUSTOMER'

export interface User {
  id: string
  full_name: string
  email: string | null
  phone: string | null
  role: UserRole
  is_active: boolean
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}
