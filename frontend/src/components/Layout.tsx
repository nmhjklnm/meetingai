import { Outlet, Link, useLocation } from "react-router-dom";
import { MicVocal, Upload, LayoutList } from "lucide-react";
import { clsx } from "clsx";

export default function Layout() {
  const { pathname } = useLocation();

  const nav = [
    { to: "/", label: "会议列表", icon: LayoutList },
    { to: "/upload", label: "上传音频", icon: Upload },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-white px-6 py-3 flex items-center gap-3">
        <MicVocal className="w-6 h-6 text-blue-600" />
        <span className="font-semibold text-lg text-gray-900">Meeting Transcriber</span>
        <nav className="ml-8 flex gap-1">
          {nav.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                pathname === to
                  ? "bg-blue-50 text-blue-600"
                  : "text-gray-600 hover:bg-gray-100"
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          ))}
        </nav>
      </header>

      {/* Main */}
      <main className="flex-1 container mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
