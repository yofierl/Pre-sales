"""材料解析服务 — 文本提取与来源块合并。"""

from pathlib import Path

from app.schemas.requirement import SourceBlock


class MergeResult:
    """合并结果。"""

    def __init__(self, blocks: list[SourceBlock], conflicts: list[str] | None = None) -> None:
        self.blocks = blocks
        self.conflicts = conflicts or []


class ParseResult:
    """单文件解析结果。"""

    def __init__(self, status: str, text: str = "", error: str = "") -> None:
        self.status = status
        self.text = text
        self.error = error


def merge_source_blocks(blocks: list[SourceBlock]) -> MergeResult:
    """按优先级（1 最高）合并来源块，返回结果和冲突列表。"""
    from collections import defaultdict

    # 按来源名分组
    by_source = defaultdict(list)
    for b in blocks:
        by_source[b.source].append(b)

    merged: list[SourceBlock] = []
    conflicts: list[str] = []

    # 按最低优先级（最高数字）排序 → 最低数字优先级最高
    sorted_sources = sorted(by_source.items(), key=lambda x: min(b.priority for b in x[1]))

    seen_texts: list[str] = []
    for source, items in sorted_sources:
        for item in items:
            if item.text:
                for seen in seen_texts:
                    # 检查简单关键词重叠（中文 4 字以上重叠即视为冲突）
                    overlap_len = 0
                    for i in range(len(item.text) - 3):
                        chunk = item.text[i:i + 4]
                        if chunk in seen:
                            overlap_len = max(overlap_len, len(chunk))
                    if overlap_len >= 4:
                        conflicts.append(f"来源 '{source}' 与已有块描述冲突: 「{item.text[:30]}」vs 「{seen[:30]}」")
                        break
                seen_texts.append(item.text)
            merged.append(item)

    merged.sort(key=lambda b: b.priority)
    return MergeResult(blocks=merged, conflicts=conflicts)


def parse_material(path: Path, mime_type: str) -> ParseResult:
    """解析单个材料文件，提取文本内容。"""
    suffix = path.suffix.lower()

    if suffix not in {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg", ".txt"}:
        return ParseResult(status="failed", error=f"不支持的文件格式: {suffix}")

    if path.stat().st_size == 0:
        return ParseResult(status="failed", error=f"空文件: {path.name}")

    try:
        content = path.read_bytes()
    except Exception as exc:
        return ParseResult(status="failed", error=f"读取文件失败 {path.name}: {exc}")

    if suffix == ".txt":
        try:
            text = content.decode("utf-8")
            return ParseResult(status="succeeded", text=text)
        except Exception as exc:
            return ParseResult(status="failed", error=f"文本解码失败: {exc}")

    # 基本格式校验
    if suffix == ".pdf" and not content.startswith(b"%PDF"):
        return ParseResult(status="failed", error=f"无效的 PDF 文件: {path.name}")
    if suffix == ".docx" and not content.startswith(b"PK"):
        return ParseResult(status="failed", error=f"无效的 DOCX 文件: {path.name}")
    if suffix == ".xlsx" and not content.startswith(b"PK"):
        return ParseResult(status="failed", error=f"无效的 XLSX 文件: {path.name}")

    # 二进制格式仅返回基本信息
    return ParseResult(
        status="succeeded",
        text=f"[{path.name}] 文件类型 {mime_type}，大小 {path.stat().st_size} 字节，待 Agent 解析",
    )
