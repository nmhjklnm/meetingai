/**
 * 会议列表页
 * ----------
 * TODO:
 * 1. GET /api/meetings → 获取历史会议列表
 * 2. 展示：标题、时长、说话人数、创建时间、状态（处理中/完成）
 * 3. 点击跳转 /meetings/:id
 */
import { Link } from "react-router-dom";
import { MicVocal, Clock, Users } from "lucide-react";

const PLACEHOLDER_MEETINGS = [
  { id: "1", title: "单聊群聊红点与channel设计探讨", duration: "82:35", speakers: 3, date: "2026-03-10", status: "done" },
  { id: "2", title: "TTC北京团队会议", duration: "91:20", speakers: 3, date: "2026-03-10", status: "done" },
];

export default function MeetingsListPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">会议记录</h1>
          <p className="text-gray-500 mt-1">共 {PLACEHOLDER_MEETINGS.length} 条记录</p>
        </div>
        <Link
          to="/upload"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          + 上传新录音
        </Link>
      </div>

      <div className="space-y-3">
        {PLACEHOLDER_MEETINGS.map((m) => (
          <Link
            key={m.id}
            to={`/meetings/${m.id}`}
            className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-blue-300 hover:shadow-sm transition-all"
          >
            <div className="flex items-start gap-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <MicVocal className="w-5 h-5 text-blue-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{m.title}</p>
                <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                  <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{m.duration}</span>
                  <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" />{m.speakers} 位说话人</span>
                  <span>{m.date}</span>
                </div>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                m.status === "done" ? "bg-green-50 text-green-700" : "bg-yellow-50 text-yellow-700"
              }`}>
                {m.status === "done" ? "已完成" : "处理中"}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
