import api from "./api";

export const listNotifications = (params) => api.get("/notifications", { params }).then((r) => r.data);
export const markNotificationRead = (id) => api.patch(`/notifications/${id}`, { is_read: true }).then((r) => r.data);
