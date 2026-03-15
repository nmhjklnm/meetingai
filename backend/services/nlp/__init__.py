"""
NLP Service — 文本智能处理
============================
对转录文本做二次分析，是与腾讯会议/飞书会议区别的核心功能：

1. 摘要（Summary）
   · 按说话人分别摘要 + 整体摘要
   · 支持自定义长度

2. 关键词 & 话题标签（Keywords）
   · 提取会议核心议题

3. 行动项（Action Items）
   · 识别 "xx负责xxx" "下次会议xx" 等承诺/任务

4. 说话人对齐（Speaker Alignment）
   · 将 Speaker A/B/C 对齐到真实姓名/角色
   · 支持手动确认

5. 情感分析（可选）
   · 检测讨论热点、分歧点
"""

from .processor import NLPService

__all__ = ["NLPService"]
