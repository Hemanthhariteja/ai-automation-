import api from "./api";

export const listLeads = (params) => api.get("/leads", { params }).then((r) => r.data);
export const getLead = (id) => api.get(`/leads/${id}`).then((r) => r.data);
export const createLead = (payload) => api.post("/leads", payload).then((r) => r.data);
export const updateLead = (id, payload) => api.patch(`/leads/${id}`, payload).then((r) => r.data);
export const deleteLead = (id) => api.delete(`/leads/${id}`);
export const classifyLead = (id) => api.post(`/leads/${id}/classify`).then((r) => r.data);
export const generateResponse = (id) => api.post(`/leads/${id}/generate-response`).then((r) => r.data);
export const getConversation = (id) => api.get(`/leads/${id}/conversation`).then((r) => r.data);
export const summarizeConversation = (id) => api.post(`/leads/${id}/summarize`).then((r) => r.data);

export const importLeadsCsv = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/leads/import", formData, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
};

export const importTemplateUrl = () => `${api.defaults.baseURL}/leads/import/template`;

export const exportLeadsCsv = (params) => api.get("/leads/export", { params, responseType: "blob" }).then((r) => r.data);
export const exportCustomersCsv = () => api.get("/leads/export/customers", { responseType: "blob" }).then((r) => r.data);

// The export endpoints need the Authorization header, so a plain <a href>
// download link won't work (browser navigation doesn't carry it) — fetch the
// CSV via axios instead and trigger the save with a throwaway object URL.
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
