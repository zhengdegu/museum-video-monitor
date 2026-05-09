import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import RoomList from '../pages/Room'
import CameraList from '../pages/Camera'
import VideoList from '../pages/Video'
import EventList from '../pages/Event'
import RuleList from '../pages/Rule'
import ChatPage from '../pages/Chat'
import CollectionList from '../pages/Collection'
import UserList from '../pages/System'
import InventoryPage from '../pages/Inventory'
import AiInventory from '../pages/Inventory/AiInventory'
import ReportPage from '../pages/Report'
import ApiKeys from '../pages/System/ApiKeys'
import Webhooks from '../pages/System/Webhooks'
import PushChannels from '../pages/System/PushChannels'
import WarningPage from '../pages/Warning'
import RoomMapPage from '../pages/Room/RoomMap'
import Nodes from '../pages/System/Nodes'
import { useAuthStore } from '../store/auth'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" />
}

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<PrivateRoute><MainLayout /></PrivateRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="rooms" element={<RoomList />} />
        <Route path="cameras" element={<CameraList />} />
        <Route path="videos" element={<VideoList />} />
        <Route path="events" element={<EventList />} />
        <Route path="warnings" element={<WarningPage />} />
        <Route path="rules" element={<RuleList />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="collections" element={<CollectionList />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="ai-inventory" element={<AiInventory />} />
        <Route path="users" element={<UserList />} />
        <Route path="api-keys" element={<ApiKeys />} />
        <Route path="webhooks" element={<Webhooks />} />
        <Route path="push-channels" element={<PushChannels />} />
        <Route path="reports" element={<ReportPage />} />
        <Route path="room-map" element={<RoomMapPage />} />
        <Route path="nodes" element={<Nodes />} />
      </Route>
    </Routes>
  )
}
