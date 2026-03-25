"""
NLP 处理器 — 基于 GPT-4o
"""

from __future__ import annotations

import os
from typing import Optional
from openai import OpenAI


SUMMARY_PROMPT = """\
你是一位会议记录整理助手。请根据以下会议转录文本，完成以下任务：

1. **整体摘要**（200字以内）：概括会议核心议题和结论
2. **会议主线时间轴**（timeline）：按时间顺序提炼 5-10 个关键节点，每个节点包含时间戳（秒数）和一句话概括该阶段讨论的核心内容。时间戳从转录文本中的时间标记推断。
3. **各说话人发言要点**：每位说话人 3-5 条要点
4. **行动项**：列出所有明确的任务、承诺或下一步行动，注明负责人
5. **关键词**：5-10 个会议相关关键词

转录文本（格式：[MM:SS] 说话人: 内容）：
{transcript}

请用 JSON 格式返回，结构如下：
{{
  "summary": "...",
  "timeline": [{{"time": 0, "title": "一句话概括"}}],
  "speakers": {{"Speaker A": ["要点1", "要点2"], ...}},
  "action_items": [{{"assignee": "...", "task": "...", "deadline": "..."}}],
  "keywords": ["...", "..."]
}}
"""


class NLPService:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        self.client = OpenAI(
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
        )
        self.model = model

    def analyze(self, transcript: str) -> dict:
        """
        对转录文本做完整分析，返回摘要/要点/行动项/关键词。
        """
        import json

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": SUMMARY_PROMPT.format(transcript=transcript)}
            ],
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(resp.choices[0].message.content)
        except json.JSONDecodeError:
            return {"raw": resp.choices[0].message.content}

    def align_speakers(
        self,
        segments: list[dict],
        speaker_map: dict[str, str],   # {"Speaker A": "张三", "Speaker B": "李四"}
    ) -> list[dict]:
        """
        将 Speaker A/B/C 替换为真实姓名。
        """
        return [
            {**seg, "speaker": speaker_map.get(seg["speaker"], seg["speaker"])}
            for seg in segments
        ]
