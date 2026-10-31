import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { RequireLogin } from '@/components/RequireLogin'
import { AppLayout } from '@/layout/AppLayout'
import ClientPage from '@/pages/clients/ClientPage'
import ClientsPage from '@/pages/clients/ClientsPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import EnquiriesPage from '@/pages/enquiries/EnquiriesPage'
import LoginPage from '@/pages/login/LoginPage'
import NotificationsPage from '@/pages/notifications/NotificationsPage'
import PaymentsPage from '@/pages/payments/PaymentsPage'
import QuotationsPage from '@/pages/quotations/QuotationsPage'
import VendorsPage from '@/pages/vendors/VendorsPage'
import WeddingsPage from '@/pages/weddings/WeddingsPage'

// Only Member 1 edits this file. Every page lives in its own folder under pages/.
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireLogin />}>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="enquiries" element={<EnquiriesPage />} />
            <Route path="clients" element={<ClientsPage />} />
            <Route path="clients/:id" element={<ClientPage />} />
            <Route path="weddings" element={<WeddingsPage />} />
            <Route path="vendors" element={<VendorsPage />} />
            <Route path="quotations" element={<QuotationsPage />} />
            <Route path="payments" element={<PaymentsPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
