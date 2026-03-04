import API from "./client";

export const createChat = async () => {
  const res = await API.post("/chats");
  return res.data;
};

export const fetchChats = async () => {
  const res = await API.get("/chats");
  return res.data;
};

export const fetchMessages = async (chatId) => {
  const res = await API.get(`/chats/${chatId}`);
  return res.data;
};

export const sendMessage = async (chatId, payload) => {
  const res = await API.post(`/chats/${chatId}/message`, payload);
  return res.data;
};