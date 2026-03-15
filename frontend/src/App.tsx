import { BrowserRouter, Routes, Route } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import MeetingPage from "./pages/MeetingPage";
import MeetingsListPage from "./pages/MeetingsListPage";
import Layout from "./components/Layout";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<MeetingsListPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/meetings/:id" element={<MeetingPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
