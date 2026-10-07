import { lazy, Suspense, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { PublicOnly, RequireAuth, RequirePermission } from '@/components/Guards'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AuthProvider } from '@/hooks/AuthContext'
import { ToastProvider } from '@/hooks/Toasts'

const page = <T extends Record<string, unknown>>(load: () => Promise<T>, name: keyof T) =>
  lazy(() => load().then((m) => ({ default: m[name] as React.ComponentType })))

const Overview = page(() => import('@/pages/Overview'), 'Overview')
const Forecast = page(() => import('@/pages/Forecast'), 'Forecast')
const Schedule = page(() => import('@/pages/Schedule'), 'Schedule')
const Email = page(() => import('@/pages/Email'), 'Email')
const Site = page(() => import('@/pages/Site'), 'Site')
const Users = page(() => import('@/pages/Users'), 'UsersPage')
const Audit = page(() => import('@/pages/Audit'), 'AuditPage')
const Account = page(() => import('@/pages/Account'), 'AccountPage')
const Guide = page(() => import('@/pages/Guide'), 'GuidePage')
const Login = page(() => import('@/pages/auth/Login'), 'Login')
const Setup = page(() => import('@/pages/auth/Setup'), 'Setup')
const ForgotPassword = page(() => import('@/pages/auth/ForgotPassword'), 'ForgotPassword')
const ResetPassword = page(() => import('@/pages/auth/ResetPassword'), 'ResetPassword')
const AcceptInvite = page(() => import('@/pages/auth/AcceptInvite'), 'AcceptInvite')

const open = (element: ReactNode) => <PublicOnly>{element}</PublicOnly>
const signedIn = (element: ReactNode) => <RequireAuth>{element}</RequireAuth>
const allowed = (permission: string, element: ReactNode) => signedIn(<RequirePermission permission={permission}>{element}</RequirePermission>)

export default function App() {
  return (
    <TooltipProvider>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Suspense fallback={<div className="min-h-screen bg-bg" />}>
              <Routes>
                <Route path="/login" element={open(<Login />)} />
                <Route path="/setup" element={open(<Setup />)} />
                <Route path="/forgot-password" element={open(<ForgotPassword />)} />
                <Route path="/reset" element={open(<ResetPassword />)} />
                <Route path="/invite" element={open(<AcceptInvite />)} />
                <Route path="/" element={signedIn(<Overview />)} />
                <Route path="/forecast" element={signedIn(<Forecast />)} />
                <Route path="/schedule" element={signedIn(<Schedule />)} />
                <Route path="/email" element={signedIn(<Email />)} />
                <Route path="/site" element={signedIn(<Site />)} />
                <Route path="/account" element={signedIn(<Account />)} />
                <Route path="/guide" element={signedIn(<Guide />)} />
                <Route path="/users" element={allowed('users.manage', <Users />)} />
                <Route path="/audit" element={allowed('audit.view', <Audit />)} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </TooltipProvider>
  )
}
