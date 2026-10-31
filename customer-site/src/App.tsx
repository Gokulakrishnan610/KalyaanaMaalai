import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

// each page is downloaded only when it is opened, so the landing page shows up faster
const Agreement = lazy(() => import('@/pages/Agreement'))
const AuthPage = lazy(() => import('@/pages/AuthPage'))
const ForgotPassword = lazy(() => import('@/pages/ForgotPassword'))
const Home = lazy(() => import('@/pages/Home'))
const Landing = lazy(() => import('@/pages/Landing'))
const Onboarding = lazy(() => import('@/pages/Onboarding'))
const Pay = lazy(() => import('@/pages/Pay'))
const SetPassword = lazy(() => import('@/pages/SetPassword'))

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="p-10 text-center text-stone-500">Loading…</div>}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/signup" element={<AuthPage mode="signup" />} />
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/start" element={<Onboarding />} />
        <Route path="/home" element={<Home />} />
        <Route path="/pay/:token" element={<Pay />} />
        <Route path="/agreement/:id" element={<Agreement />} />
        <Route path="/set-password" element={<SetPassword />} />
        <Route path="/forgot" element={<ForgotPassword />} />
        <Route path="*" element={<Landing />} />
      </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
