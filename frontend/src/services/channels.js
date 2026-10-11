import api from "./api";

export const getChannelsStatus = () => api.get("/channels/status").then((r) => r.data);
export const simulateMessengerMessage = (payload) =>
  api.post("/channels/messenger/simulate", payload).then((r) => r.data);
