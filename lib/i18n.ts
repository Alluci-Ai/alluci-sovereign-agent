import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      "common": {
        "connecting": "Connecting...",
        "connected": "Connected",
        "disconnected": "Disconnected",
        "cancel": "Cancel",
        "submit": "Submit",
        "error": "Error"
      },
      "debug": {
          "title": "System Diagnostics & Debug Module",
          "event_log": "Event Log",
          "rpc_console": "RPC Console",
          "security_audit": "Security Audit",
          "health_matrix": "Health Matrix",
          "awaiting_data": "AWAITING_WS_DATA_PACKETS..."
      }
    }
  },
  'zh-CN': {
    translation: {
      "common": {
        "connecting": "连接中...",
        "connected": "已连接",
        "disconnected": "未连接",
        "cancel": "取消",
        "submit": "提交",
        "error": "错误"
      },
      "debug": {
          "title": "系统诊断与调试模块",
          "event_log": "事件日志",
          "rpc_console": "RPC 控制台",
          "security_audit": "安全审计",
          "health_matrix": "运行状态矩阵",
          "awaiting_data": "正等待 WebSocket 数据包..."
      }
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: localStorage.getItem('OS_LOCALE') || 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
