"""材料解析单元测试 — 优先级合并与损坏文件处理。"""

from app.services.material_parser import merge_source_blocks, parse_material, SourceBlock


def test_merge_blocks_uses_declared_precedence():
    blocks = [
        SourceBlock(source="image.png", priority=4, text="项目名称：客户门户系统"),
        SourceBlock(source="brief.docx", priority=3, text="项目名称：新一代客户门户"),
        SourceBlock(source="user_input", priority=1, text="项目名称改为了 CRM 系统"),
    ]
    result = merge_source_blocks(blocks)
    assert result.blocks[0].source == "user_input"
    assert any("冲突" in c or "重叠" in c for c in result.conflicts)


def test_broken_file_becomes_visible_failure(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"not a pdf")
    result = parse_material(path, "application/pdf")
    assert result.status == "failed"
    assert "broken.pdf" in result.error


def test_parse_unsupported_format(tmp_path):
    path = tmp_path / "script.exe"
    path.write_bytes(b"fake binary")
    result = parse_material(path, "application/x-msdownload")
    assert result.status == "failed"
    assert "不支持的文件格式" in result.error


def test_parse_empty_file_is_failure(tmp_path):
    path = tmp_path / "empty.docx"
    path.write_bytes(b"")
    result = parse_material(path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert result.status == "failed"


def test_source_block_requires_text_or_image():
    import pydantic
    try:
        SourceBlock(source="test", priority=2)
    except pydantic.ValidationError as exc:
        errors = exc.errors()
        # Pydantic 中文错误信息，检查是否提示了 text/image_path
        messages = [str(e.get("msg", "") or e.get("message", "")) for e in errors]
        assert any("text" in m or "image" in m.lower() or "图片" in m or "文本" in m for m in messages)
