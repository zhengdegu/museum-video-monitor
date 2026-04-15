import type { ThemeConfig } from 'antd'

// WanderMap Design System Colors
export const wanderMapColors = {
  primary: '#0F766E',
  secondary: '#F97316',
  tertiary: '#0EA5E9',
  background: '#FFFFFF',
  surface: '#FFFFFF',
  success: '#059669',
  warning: '#D97706',
  error: '#EF4444',
  info: '#0EA5E9',
  textPrimary: '#1A2332',
  textSecondary: '#64748B',
  siderBg: '#0F766E',
  siderDarkBg: '#0A5C56',
}

const theme: ThemeConfig = {
  token: {
    colorPrimary: wanderMapColors.primary,
    colorSuccess: wanderMapColors.success,
    colorWarning: wanderMapColors.warning,
    colorError: wanderMapColors.error,
    colorInfo: wanderMapColors.info,
    colorLink: wanderMapColors.tertiary,
    colorBgLayout: wanderMapColors.background,
    colorBgContainer: wanderMapColors.surface,
    borderRadius: 12,
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
  },
  components: {
    Button: {
      borderRadius: 10,
      controlHeight: 40,
    },
    Card: {
      borderRadiusLG: 12,
    },
    Input: {
      borderRadius: 10,
      controlHeight: 44,
    },
    Menu: {
      darkItemBg: 'transparent',
      darkItemSelectedBg: 'rgba(255,255,255,0.15)',
      darkItemHoverBg: 'rgba(255,255,255,0.1)',
      darkItemColor: 'rgba(255,255,255,0.85)',
      darkItemSelectedColor: '#ffffff',
      itemBorderRadius: 8,
      iconSize: 18,
      itemMarginInline: 8,
    },
    Table: {
      borderRadiusLG: 12,
    },
  },
}

export default theme
