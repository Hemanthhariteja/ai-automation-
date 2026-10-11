import api from "./api";

export const getPublicBusinessInfo = (slug) => api.get(`/public/${slug}/business`).then((r) => r.data);
export const submitPublicEnquiry = (slug, payload) => api.post(`/public/${slug}/leads`, payload).then((r) => r.data);
