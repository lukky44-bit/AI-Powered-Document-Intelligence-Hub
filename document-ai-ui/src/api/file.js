import API from "./client";

export const fetchMyFiles=async()=>{
    const res=await API.get("/files/my");
    return res.data.files ||[];
};

export const deleteFile=async (fileId)=>{
    const res=await API.delete(`/files/${fileId}`);
    return res.data;
};