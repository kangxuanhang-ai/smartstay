import type { ThemeConfig } from 'antd'

const theme: ThemeConfig = {
  token: {
    colorPrimary: '#1677ff',
    colorBgLayout: '#f1f5f9',
    colorBgContainer: '#ffffff',
    colorText: '#1e293b',
    colorTextSecondary: '#64748b',
    colorTextTertiary: '#94a3b8',
    colorBorder: '#e2e8f0',
    borderRadius: 8,
    fontSize: 14,
    controlHeight: 36,
    lineHeight: 1.6,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  components: {
    Card: {
      paddingLG: 20,
      borderRadiusLG: 10,
    },
    Table: {
      headerBg: '#f8fafc',
      borderColor: '#e2e8f0',
    },
    Tag: {
      borderRadiusSM: 4,
    },
    Menu: {
      darkItemBg: '#001529',
      darkItemColor: '#ffffffb3',
      darkItemSelectedBg: '#1677ff',
    },
    Layout: {
      headerBg: '#ffffff',
      siderBg: '#001a33',
    },
  },
}

export default theme
