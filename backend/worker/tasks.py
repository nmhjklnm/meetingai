"""
Celery 异步任务
===============
音频处理 Pipeline 作为后台任务运行，前端通过 WebSocket 接收实时进度。

任务流程：
  1. process_audio_task
     ├─ step 1: 格式转换（ffmpeg）
     ├─ step 2: VAD（Silero）
     ├─ step 3: 说话人分离（ECAPA-TDNN）
     ├─ step 4: 并发转写（GPT-4o-transcribe）
     ├─ step 5: NLP 分析（GPT-4o 摘要/行动项）
     └─ step 6: 保存结果到数据库

TODO:
  pip install celery redis
  celery -A backend.worker.tasks worker --loglevel=info
"""

# from celery import Celery
# from backend.core.config import settings
#
# celery_app = Celery("meeting_transcriber", broker=settings.REDIS_URL)
#
# @celery_app.task(bind=True)
# def process_audio_task(self, meeting_id: str, audio_path: str):
#     ...
