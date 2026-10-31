import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { RequireLogin } from '@/components/RequireLogin'
import { AppLayout } from '@/layout/AppLayout'
import CheckinPage from '@/pages/checkin/PublicCheckinPage'
import ClientPage from '@/pages/clients/ClientPage'
import ClientsPage from '@/pages/clients/ClientsPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import EnquiriesPage from '@/pages/enquiries/EnquiriesPage'
import IncidentsPage from '@/pages/incidents/IncidentsPage'
import LoginPage from '@/pages/login/LoginPage'
import NotificationsPage from '@/pages/notifications/NotificationsPage'
import PublicPayPage from '@/pages/pay/PublicPayPage'
import PaymentsPage from '@/pages/payments/PaymentsPage'
import QuotationsPage from '@/pages/quotations/QuotationsPage'
import RequestDetailPage from '@/pages/quotations/RequestDetailPage'
import VendorProfilePage from '@/pages/vendors/VendorProfilePage'
import VendorsPage from '@/pages/vendors/VendorsPage'
import WeddingDetailPage from '@/pages/weddings/WeddingDetailPage'
import WeddingsPage from '@/pages/weddings/WeddingsPage'

// Only Member 1 edits this file. Every page lives in its own folder under pages/.
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/checkin/:token" element={<CheckinPage />} />
        <Route path="/pay/:token" element={<PublicPayPage />} />
        <Route element={<RequireLogin />}>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="enquiries" element={<EnquiriesPage />} />
            <Route path="clients" element={<ClientsPage />} />
            <Route path="clients/:id" element={<ClientPage />} />
            <Route path="weddings" element={<WeddingsPage />} />
            <Route path="weddings/:id" element={<WeddingDetailPage />} />
            <Route path="vendors" element={<VendorsPage />} />
            <Route path="vendors/:id" element={<VendorProfilePage />} />
            <Route path="quotations" element={<QuotationsPage />} />
            <Route path="quotations/:id" element={<RequestDetailPage />} />
            <Route path="incidents" element={<IncidentsPage />} />
            <Route path="payments" element={<PaymentsPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
