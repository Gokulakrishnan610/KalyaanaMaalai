import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AuthPage from '@/pages/AuthPage'
import Home from '@/pages/Home'
import Landing from '@/pages/Landing'
import Onboarding from '@/pages/Onboarding'
import Pay from '@/pages/Pay'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/signup" element={<AuthPage mode="signup" />} />
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/start" element={<Onboarding />} />
        <Route path="/home" element={<Home />} />
        <Route path="/pay/:token" element={<Pay />} />
        <Route path="*" element={<Landing />} />
      </Routes>
    </BrowserRouter>
  )
}
