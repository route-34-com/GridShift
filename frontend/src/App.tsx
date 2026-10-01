import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { RunProvider } from '@/hooks/RunContext'

const Overview = lazy(() => import('@/pages/Overview').then((m) => ({ default: m.Overview })))
const Forecast = lazy(() => import('@/pages/Forecast').then((m) => ({ default: m.Forecast })))
const Schedule = lazy(() => import('@/pages/Schedule').then((m) => ({ default: m.Schedule })))
const Email = lazy(() => import('@/pages/Email').then((m) => ({ default: m.Email })))
const Site = lazy(() => import('@/pages/Site').then((m) => ({ default: m.Site })))

export default function App() {
  return (
    <TooltipProvider>
      <RunProvider>
        <BrowserRouter>
          <Suspense fallback={<div className="min-h-screen bg-bg" />}>
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/forecast" element={<Forecast />} />
              <Route path="/schedule" element={<Schedule />} />
              <Route path="/email" element={<Email />} />
              <Route path="/site" element={<Site />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </RunProvider>
    </TooltipProvider>
  )
}
