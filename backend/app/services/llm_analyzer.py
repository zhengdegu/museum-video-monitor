"""大模型分析服务 (Qwen3.5 多模态 + Qwen3 文本)"""
import base64
import json
import logging
import os
import re
from typing import List, Dict, Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """调用 vLLM 进行多模态视频帧分析和裁判结论"""

    def __init__(self):
        self.vision_client = AsyncOpenAI(base_url=settings.VLLM_VISION_URL, api_key=settings.VLLM_API_KEY)
        self.text_client = AsyncOpenAI(base_url=settings.VLLM_TEXT_URL, api_key=settings.VLLM_API_KEY)
        self.vision_model = settings.VLLM_VISION_MODEL
        self.text_model = settings.VLLM_TEXT_MODEL

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def analyze_segment(self, frame_paths: List[str], yolo_results: Dict, pose_results: Dict) -> str:
        """分析单个60s片段：截图 + YOLO/Pose结果 → Qwen3.5 多模态分析"""
        try:
            # 构造图片内容（最多取15帧避免token过长）
            step = max(1, len(frame_paths) // 15)
            selected_frames = frame_paths[::step][:15]

            image_contents = []
            for fp in selected_frames:
                if os.path.exists(fp):
                    b64 = self._encode_image(fp)
                    image_contents.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    })

            prompt = f"""你是博物馆安防视频分析专家。请分析以下监控画面截图。

YOLO检测结果：
- 检测到人数：{yolo_results.get('person_count', '未知')}
- 检测框信息：{yolo_results.get('boxes', [])}

姿态分析结果：
- 姿态信息：{pose_results.get('postures', [])}
- 是否检测到奔跑：{pose_results.get('running_detected', False)}

请分析并输出：
1. 画面中的人数（精确）
2. 着装情况（是否统一工作服、是否携带背包等）
3. 行为描述（正常操作/奔跑/跳跃/躲藏等）
4. 手持物品情况（是否双手持有文物、是否有人监督）
5. 整体安全评估

请用简洁中文回答，结构化输出。"""

            messages = [{"role": "user", "content": [{"type": "text", "text": prompt}] + image_contents}]

            response = await self.vision_client.chat.completions.create(
                model=self.vision_model,
                messages=messages,
                max_tokens=2000,
                temperature=0.1,
            )
            result = response.choices[0].message.content
            logger.info(f"片段分析完成: {len(selected_frames)} 帧")
            return result

        except Exception as e:
            logger.error(f"片段分析失败: {e}")
            return f"分析失败: {str(e)}"

    async def merge_conclusions(self, current: str, previous: str) -> str:
        """增量合并结论：将当前片段结论与前序结论压缩合并"""
        if not previous:
            return current

        try:
            prompt = f"""请将以下两段视频分析结论合并为一份简洁的综合结论，保留关键信息，去除重复内容。

前序结论：
{previous}

当前片段结论：
{current}

请输出合并后的综合结论，保持结构化格式。"""

            response = await self.text_client.chat.completions.create(
                model=self.text_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.1,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"结论合并失败: {e}")
            return f"{previous}\n---\n{current}"

    async def judge(self, merged_conclusion: str, rules: List[Dict]) -> Dict:
        """裁判模型：结合合并结论 + 规则列表，输出最终判定"""
        try:
            rules_text = "\n".join([
                f"- {r['name']}({r['code']}): {r['description']}"
                for r in rules if r.get('enabled', 1) == 1
            ])

            prompt = f"""你是博物馆安防规则裁判。请根据以下视频分析结论，判定是否命中安防规则。

视频分析结论：
{merged_conclusion}

安防规则列表：
{rules_text}

请逐条规则判定，输出 JSON 格式：
{{
  "summary": "整体评估摘要",
  "risk_level": 0-3 (0正常 1低风险 2中风险 3高风险),
  "rule_hits": [
    {{
      "rule_code": "规则编码",
      "hit": true/false,
      "confidence": 0.0-1.0,
      "detail": "命中详情说明"
    }}
  ]
}}

只输出 JSON，不要其他内容。"""

            response = await self.text_client.chat.completions.create(
                model=self.text_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.1,
            )

            text = response.choices[0].message.content.strip()
            return self._parse_json_robust(text)

        except Exception as e:
            logger.error(f"裁判判定失败: {e}")
            return {"summary": f"判定失败: {str(e)}", "risk_level": 0, "rule_hits": []}

    @staticmethod
    def _parse_json_robust(text: str) -> Dict:
        """多层 fallback 的 JSON 解析"""
        # 1. 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. 提取 ```json ... ``` 代码块
        md_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if md_match:
            try:
                return json.loads(md_match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. 提取 ``` ... ``` 代码块
        code_match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except json.JSONDecodeError:
                pass

        # 4. 正则提取最外层 { ... }
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        # 5. 全部失败，返回兜底结构
        logger.warning(f"JSON 解析全部失败，原始文本: {text[:200]}")
        return {"summary": text[:500], "risk_level": 0, "rule_hits": []}


# 全局单例
llm_analyzer = LLMAnalyzer()
