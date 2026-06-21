import { http } from './http'

export interface User {
  id: string
  username: string
}

export interface LoginPayload {
  username: string
  password: string
}

export async function login(payload: LoginPayload): Promise<User> {
  const response = await http.post<User>('/auth/login', payload)
  return response.data
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await http.get<User>('/auth/me')
  return response.data
}

export async function logout(): Promise<void> {
  await http.post('/auth/logout')
}

