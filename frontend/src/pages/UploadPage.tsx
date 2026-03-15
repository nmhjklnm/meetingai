/**
 * 上传页面
 * --------
 * TODO:
 * 1. 拖拽上传音频文件（支持 mp3/m4a/wav/mp4）
 * 2. 显示文件信息（时长、大小）
 * 3. POST /api/meetings → 创建任务
 * 4. 跳转到 /meetings/:id 查看实时进度
 */
import { Upload } from "lucide-react";

export default function UploadPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">上传会议录音</h1>
        <p className="text-gray-500 mt-1">支持 MP3、M4A、WAV、MP4 格式，最大 2GB</p>
      </div>

      {/* Drop zone */}
      <div className="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center hover:border-blue-400 hover:bg-blue-50 transition-colors cursor-pointer">
        <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
        <p className="text-gray-600 font-medium">拖拽文件到这里，或点击上传</p>
        <p className="text-gray-400 text-sm mt-1">也可以一次上传多个文件（同一场会议的多个录音段）</p>
        <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          选择文件
        </button>
      </div>

      {/* TODO: 文件列表 + 上传进度 */}
    </div>
  );
}
