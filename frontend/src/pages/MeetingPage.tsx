/**
 * 会议详情页
 * ----------
 * TODO:
 * 1. GET /api/meetings/:id → 会议详情 + 转录结果
 * 2. 三栏布局：
 *    - 左：说话人列表（可编辑姓名）
 *    - 中：转录文本（按说话人着色，点击跳音频）
 *    - 右：AI 摘要 + 行动项
 * 3. WS /ws/meetings/:id/progress → 实时转写进度
 * 4. 导出按钮：SRT / TXT / DOCX
 */
import { useParams } from "react-router-dom";
import { Users, FileText, Sparkles } from "lucide-react";

export default function MeetingPage() {
  const { id } = useParams();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">会议详情 #{id}</h1>
        <div className="flex gap-2">
          <button className="px-3 py-1.5 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">
            导出 SRT
          </button>
          <button className="px-3 py-1.5 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">
            导出 TXT
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* 说话人面板 */}
        <aside className="col-span-2 space-y-3">
          <div className="flex items-center gap-1.5 text-sm font-medium text-gray-500">
            <Users className="w-4 h-4" /> 说话人
          </div>
          {["Speaker A", "Speaker B", "Speaker C"].map((spk, i) => (
            <div key={i} className="p-2 bg-white rounded-lg border text-sm">
              <div className={`w-2 h-2 rounded-full inline-block mr-1.5 ${
                ["bg-blue-500", "bg-green-500", "bg-purple-500"][i]
              }`} />
              <span className="text-gray-500">{spk}</span>
              {/* TODO: 可点击编辑为真实姓名 */}
            </div>
          ))}
        </aside>

        {/* 转录文本 */}
        <main className="col-span-7 bg-white rounded-xl border p-4 space-y-3 min-h-96">
          <div className="flex items-center gap-1.5 text-sm font-medium text-gray-500 mb-4">
            <FileText className="w-4 h-4" /> 转录文本
          </div>
          {/* TODO: 从 API 加载真实转录数据 */}
          <p className="text-gray-400 text-sm text-center py-12">
            正在加载转录结果...
          </p>
        </main>

        {/* AI 摘要 */}
        <aside className="col-span-3 space-y-4">
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-1.5 text-sm font-medium text-gray-500 mb-3">
              <Sparkles className="w-4 h-4 text-yellow-500" /> AI 摘要
            </div>
            {/* TODO: GET /api/meetings/:id/summary */}
            <p className="text-gray-400 text-sm">摘要生成中...</p>
          </div>

          <div className="bg-white rounded-xl border p-4">
            <p className="text-sm font-medium text-gray-500 mb-3">行动项</p>
            {/* TODO: 从摘要 API 加载 action_items */}
            <p className="text-gray-400 text-sm">暂无行动项</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
