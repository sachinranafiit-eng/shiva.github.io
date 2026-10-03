export const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
export type User = { id: number; username: string; first_name: string; last_name: string; email: string; role: string; phone: string }
export type Service = { id: number; category: string; name: string; description: string; labour_price: string; visit_price: string; tax_rate: string; image: string; image_url: string }
export type ServiceArea = { id: number; name: string; city: string; postal_code: string; services: number[] }
export type AvailabilitySlot = { id: number; service: number; starts_at: string; ends_at: string; capacity: number; remaining: number }
export type Offer = { id: number; code: string; title: string; description: string; service: number | null; discount_type: string; value: string; ends_at: string }
export type Product = { id: number; sku: string; name: string; brand: string; category: string; description: string; unit: string; price: string; tax_rate: string; available: number; image_url: string; image: string }
export type Address = { id: number; label: string; line: string; city: string; postal_code: string }
export type Estimate = { id: number; booking: number; status: string; note: string; lines: { id: number; product: number; product_name: string; quantity: number; unit_price: string; tax_rate: string; issued: boolean }[] }
export type Booking = { id: number; service: number; service_name: string; customer_name: string; customer_phone: string; address: number; address_text: string; issue: string; preferred_at: string; urgency: string; mode: string; status: string; diagnosis: string; job_notes: string; labour_charge: string | null; estimates: Estimate[]; job_photos: { id: number; image: string; caption: string }[]; activity: { id: number; actor_name: string; message: string; created_at: string }[]; technician: number | null; invoice: null | { id: number; payment_method: string; charges: { labour: string; visit: string; discount: string; offer_code: string; service_tax: string; materials: { product: string; quantity: number; base: string; tax: string }[]; total: string } } }
export function getToken() { return sessionStorage.getItem('shiva_token') || '' }
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!API_URL) throw new Error('Booking API is not configured yet. Please call +91 9259599151.')
  const token = getToken()
  const headers: Record<string, string> = { ...(options.headers as Record<string, string> || {}) }
  if (token) headers.Authorization = `Token ${token}`
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  let response: Response
  try { response = await fetch(`${API_URL}${path}`, { ...options, headers }) }
  catch { throw new Error('Booking server is unavailable. Please try later or call +91 9259599151.') }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data))
  return data as T
}
export async function all<T>(path: string): Promise<T[]> { const data = await api<{ results: T[] } | T[]>(path); return Array.isArray(data) ? data : data.results }
export function money(v: string | number) { return `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 })}` }
