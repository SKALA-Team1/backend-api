"""
PDF Parser
==========
교재 PDF를 파싱하여 텍스트와 목차(TOC)를 추출하는 모듈.

역할:
    - PDF 파일에서 텍스트 추출
    - PDF 내장 목차(TOC/Bookmark) 추출
    - 페이지별 텍스트 추출
    - 목차 기반 섹션 분리

의존성:
    - pymupdf (fitz)
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class TOCEntry:
    """목차 항목"""
    level: int  # 목차 깊이 (1, 2, 3...)
    title: str  # 제목
    page_num: int  # 페이지 번호
    children: list["TOCEntry"] = field(default_factory=list)


@dataclass
class Section:
    """섹션 (목차 기반 분리된 텍스트 단위)"""
    title: str
    level: int
    start_page: int
    end_page: int
    text: str
    metadata: dict = field(default_factory=dict)


class PDFParser:
    """PDF 파서 클래스"""

    def __init__(self, pdf_path: str | Path):
        """
        Args:
            pdf_path: PDF 파일 경로
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        self.doc: Optional[fitz.Document] = None
        self._toc: list[TOCEntry] = []

    def open(self) -> "PDFParser":
        """PDF 파일 열기"""
        self.doc = fitz.open(str(self.pdf_path))
        logger.info(f"Opened PDF: {self.pdf_path.name}, pages: {len(self.doc)}")
        return self

    def close(self):
        """PDF 파일 닫기"""
        if self.doc:
            self.doc.close()
            self.doc = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def page_count(self) -> int:
        """전체 페이지 수"""
        return len(self.doc) if self.doc else 0

    def get_toc(self) -> list[TOCEntry]:
        """
        PDF 내장 목차(TOC) 추출

        Returns:
            목차 항목 리스트
        """
        if not self.doc:
            raise RuntimeError("PDF not opened. Call open() first.")

        raw_toc = self.doc.get_toc()  # [[level, title, page], ...]

        if not raw_toc:
            logger.warning("No TOC found in PDF")
            return []

        toc_entries = []
        for item in raw_toc:
            level, title, page_num = item[0], item[1], item[2]
            entry = TOCEntry(
                level=level,
                title=title.strip(),
                page_num=page_num
            )
            toc_entries.append(entry)

        self._toc = toc_entries
        logger.info(f"Extracted {len(toc_entries)} TOC entries")
        return toc_entries

    def get_page_text(self, page_num: int) -> str:
        """
        특정 페이지의 텍스트 추출

        Args:
            page_num: 페이지 번호 (0-based)

        Returns:
            페이지 텍스트
        """
        if not self.doc:
            raise RuntimeError("PDF not opened. Call open() first.")

        if page_num < 0 or page_num >= len(self.doc):
            raise ValueError(f"Invalid page number: {page_num}")

        page = self.doc[page_num]
        return page.get_text()

    def get_text_range(self, start_page: int, end_page: int) -> str:
        """
        페이지 범위의 텍스트 추출

        Args:
            start_page: 시작 페이지 (0-based, inclusive)
            end_page: 끝 페이지 (0-based, exclusive)

        Returns:
            결합된 텍스트
        """
        if not self.doc:
            raise RuntimeError("PDF not opened. Call open() first.")

        texts = []
        for page_num in range(start_page, min(end_page, len(self.doc))):
            texts.append(self.get_page_text(page_num))

        return "\n\n".join(texts)

    def get_all_text(self) -> str:
        """전체 PDF 텍스트 추출"""
        return self.get_text_range(0, self.page_count)

    def extract_sections_by_toc(self, target_level: int = 1) -> list[Section]:
        """
        목차 기반으로 섹션 분리

        Args:
            target_level: 분리 기준 목차 레벨 (1=대단원, 2=중단원 등)

        Returns:
            섹션 리스트
        """
        if not self._toc:
            self.get_toc()

        if not self._toc:
            logger.warning("No TOC available for section extraction")
            return []

        # target_level 이하의 항목만 필터
        filtered_entries = [e for e in self._toc if e.level <= target_level]

        if not filtered_entries:
            logger.warning(f"No TOC entries at level {target_level}")
            return []

        sections = []
        for i, entry in enumerate(filtered_entries):
            # 다음 섹션의 시작 페이지 또는 문서 끝
            if i + 1 < len(filtered_entries):
                end_page = filtered_entries[i + 1].page_num - 1
            else:
                end_page = self.page_count

            start_page = entry.page_num - 1  # 0-based로 변환

            # 텍스트 추출
            text = self.get_text_range(start_page, end_page)

            section = Section(
                title=entry.title,
                level=entry.level,
                start_page=entry.page_num,
                end_page=end_page,
                text=text,
                metadata={
                    "source": self.pdf_path.name,
                    "section_index": i
                }
            )
            sections.append(section)

        logger.info(f"Extracted {len(sections)} sections at level {target_level}")
        return sections

    def print_toc_tree(self) -> str:
        """목차를 트리 형태로 출력"""
        if not self._toc:
            self.get_toc()

        lines = ["=" * 50, "TABLE OF CONTENTS", "=" * 50]

        for entry in self._toc:
            indent = "  " * (entry.level - 1)
            lines.append(f"{indent}[{entry.level}] {entry.title} (p.{entry.page_num})")

        lines.append("=" * 50)
        return "\n".join(lines)


def extract_toc_from_content(pdf_path: str | Path) -> list[TOCEntry]:
    """
    PDF 내용에서 목차 패턴을 분석하여 TOC 추출 (AGS 교재 전용)

    AGS 교재 목차 구조:
    - Chapter 01, Chapter 02, Chapter 03 (3개 연속)
    - 영문 제목 3개
    - 한글 제목 3개
    - 페이지 번호 3개
    - Unit 제목
    - Unit 번호

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        목차 항목 리스트
    """
    import re

    toc_entries = []

    with PDFParser(pdf_path) as parser:
        # 목차 페이지 (보통 3페이지) 텍스트 추출
        toc_text = parser.get_page_text(2)  # 0-indexed, 3페이지

        lines = [line.strip() for line in toc_text.split('\n')]

        # Chapter 번호들 수집
        chapter_indices = []
        for i, line in enumerate(lines):
            if re.match(r'Chapter\s+\d+$', line):
                chapter_indices.append(i)

        # 3개씩 그룹으로 처리
        for group_start in range(0, len(chapter_indices), 3):
            group_end = min(group_start + 3, len(chapter_indices))
            chapter_group = chapter_indices[group_start:group_end]

            if len(chapter_group) < 3:
                continue

            # Chapter 번호 추출
            chapter_nums = []
            for idx in chapter_group:
                match = re.match(r'Chapter\s+(\d+)$', lines[idx])
                if match:
                    chapter_nums.append(int(match.group(1)))

            # 마지막 Chapter 인덱스 이후의 라인들에서 제목과 페이지 추출
            last_chapter_idx = chapter_group[-1]

            # 다음 라인들 수집 (다음 Chapter 또는 Unit까지)
            content_lines = []
            for i in range(last_chapter_idx + 1, len(lines)):
                if re.match(r'Chapter\s+\d+$', lines[i]) or lines[i] == 'CONTENTS':
                    break
                if lines[i]:  # 빈 줄 제외
                    content_lines.append(lines[i])

            # 제목과 페이지 번호 분리
            titles_en = []
            titles_kr = []
            page_nums = []

            for content in content_lines:
                # 페이지 번호인지 확인
                if re.match(r'^\d+$', content):
                    page_nums.append(int(content))
                # Unit 번호/제목은 무시
                elif re.match(r'^Unit\s+\d+$', content):
                    continue
                # 한글이 포함된 제목
                elif re.search(r'[가-힣]', content):
                    titles_kr.append(content)
                # 영문 제목
                else:
                    titles_en.append(content)

            # Chapter 항목 생성
            for i, ch_num in enumerate(chapter_nums):
                title_en = titles_en[i] if i < len(titles_en) else ""
                title_kr = titles_kr[i] if i < len(titles_kr) else ""
                page_num = page_nums[i] if i < len(page_nums) else 1

                full_title = f"Chapter {ch_num:02d}: {title_en}"
                if title_kr:
                    full_title += f" ({title_kr})"

                entry = TOCEntry(
                    level=2,
                    title=full_title,
                    page_num=page_num
                )
                toc_entries.append(entry)

    # 페이지 번호로 정렬
    toc_entries.sort(key=lambda x: x.page_num)

    # Answer Key 추가
    toc_entries.append(TOCEntry(
        level=2,
        title="Answer Key",
        page_num=86
    ))

    logger.info(f"Extracted {len(toc_entries)} chapters from content")
    return toc_entries


def analyze_pdf_structure(pdf_path: str | Path) -> dict:
    """
    PDF 구조 분석 유틸리티

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        분석 결과 딕셔너리
    """
    with PDFParser(pdf_path) as parser:
        toc = parser.get_toc()

        # 레벨별 통계
        level_counts = {}
        for entry in toc:
            level_counts[entry.level] = level_counts.get(entry.level, 0) + 1

        return {
            "file_name": parser.pdf_path.name,
            "total_pages": parser.page_count,
            "toc_entries": len(toc),
            "level_distribution": level_counts,
            "toc_preview": [
                {"level": e.level, "title": e.title, "page": e.page_num}
                for e in toc[:20]  # 처음 20개만
            ]
        }
