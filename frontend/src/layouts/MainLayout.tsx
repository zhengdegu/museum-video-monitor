import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, theme } from 'antd'
import {
  DashboardOutlined, VideoCameraOutlined, BankOutlined,
  AlertOutlined, SafetyCertificateOutlined, MessageOutlined,
  GoldOutlined, UserOutlined, CameraOutlined, LogoutOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../store/auth'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/rooms', icon: <BankOutlined />, label: '库房管理' },
  { key: '/cameras', icon: <CameraOutlined />, label: '摄像头管理' },
  { key: '/videos', icon: <VideoCameraOutlined />, label: '视频管理' },
  { key: '/events', icon: <AlertOutlined />, label: '事件中心' },
  { key: '/rules', icon: <SafetyCertificateOutlined />, label: '规则管理' },
  { key: '/chat', icon: <MessageOutlined />, label: '智能交互' },
  { key: '/collections', icon: <GoldOutlined />, label: '藏品管理' },
  { key: '/users', icon: <UserOutlined />, label: '用户管理' },
]

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)
  const { token: { colorBgContainer, borderRadiusLG } } = theme.useToken()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="dark">
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: collapsed ? 14 : 16, fontWeight: 'bold' }}>
          {collapsed ? '监控' : '视频智能监控平台'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: '0 16px', background: colorBgContainer, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Button type="text" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed(!collapsed)} />
          <Button type="text" icon={<LogoutOutlined />} onClick={() => { logout(); navigate('/login') }}>退出</Button>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: colorBgContainer, borderRadius: borderRadiusLG, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
