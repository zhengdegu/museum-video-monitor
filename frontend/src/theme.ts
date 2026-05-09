import type { ThemeConfig } from 'antd'

// Genesis Design System Colors
export const genesisColors = {
  primary: '#6366F1',
  primaryHover: '#4F46E5',
  secondary: '#20970B',
  neutral: '#9C9C9C',
  background: '#FAFAFA',
  surface: '#FFFFFF',
  textPrimary: '#0A0A0A',
  textSecondary: '#6B6B6B',
  border: '#E8E8EC',
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
}

// Keep backward-compatible alias
export const wanderMapColors = genesisColors

const theme: ThemeConfig = {
  token: {
    colorPrimary: genesisColors.primary,
    colorSuccess: genesisColors.success,
    colorWarning: genesisColors.warning,
    colorError: genesisColors.error,
    colorInfo: genesisColors.primary,
    colorLink: genesisColors.primary,
    colorBgLayout: genesisColors.background,
    colorBgContainer: genesisColors.surface,
    colorBorder: genesisColors.border,
    colorBorderSecondary: genesisColors.border,
    borderRadius: 6,
    borderRadiusLG: 12,
    fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontFamilyCode: "'JetBrains Mono', monospace",
    fontSize: 14,
    colorText: genesisColors.textPrimary,
    colorTextSecondary: genesisColors.textSecondary,
  },
  components: {
    Button: {
      borderRadius: 6,
      controlHeight: 38,
      primaryShadow: 'none',
      defaultShadow: 'none',
      dangerShadow: 'none',
    },
    Card: {
      borderRadiusLG: 12,
      boxShadowTertiary: 'none',
    },
    Input: {
      borderRadius: 6,
      controlHeight: 38,
    },
    Select: {
      borderRadius: 6,
      controlHeight: 38,
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: genesisColors.background,
      itemSelectedColor: genesisColors.textPrimary,
      itemHoverBg: genesisColors.background,
      itemBorderRadius: 8,
      iconSize: 18,
      itemMarginInline: 8,
      subMenuItemBg: 'transparent',
    },
    Table: {
      borderRadiusLG: 12,
      headerBg: genesisColors.surface,
      headerColor: genesisColors.textSecondary,
    },
    Tag: {
      borderRadiusSM: 9999,
    },
    Tabs: {
      inkBarColor: genesisColors.primary,
      itemActiveColor: genesisColors.primary,
      itemSelectedColor: genesisColors.primary,
    },
    Layout: {
      siderBg: genesisColors.surface,
      headerBg: genesisColors.surface,
      bodyBg: genesisColors.background,
    },
  },
}

export default theme
