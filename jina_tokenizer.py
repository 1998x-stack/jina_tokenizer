#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文本分块处理工具

该模块提供了文本分析和分块的功能，支持Markdown语法结构的识别和处理。
包括对表情符号、Unicode字符等特殊内容的处理。

Author: XM
Date: 2024-02-06
"""

import regex as re
import time
import sys
from typing import List
from dataclasses import dataclass
import resource


@dataclass
class TextChunk:
    """文本块的数据类，用于存储分块结果和相关信息"""
    content: str
    chunk_type: str
    start_pos: int
    end_pos: int


class TextConstants:
    """文本处理相关的常量定义"""
    
    # 各类内容的最大长度限制
    MAX_HEADING_LENGTH: int = 7  # 最大标题长度为7
    MAX_HEADING_CONTENT_LENGTH: int = 200  # 最大标题内容长度为200
    MAX_HEADING_UNDERLINE_LENGTH: int = 200  # 最大标题下划线长度为200
    MAX_HTML_HEADING_ATTRIBUTES_LENGTH: int = 100  # 最大HTML标题属性长度为100
    MAX_LIST_ITEM_LENGTH: int = 200  # 最大列表项内容长度为200
    MAX_NESTED_LIST_ITEMS: int = 6  # 最大嵌套列表项数为6
    MAX_LIST_INDENT_SPACES: int = 7  # 最大列表项缩进空格数为7
    MAX_BLOCKQUOTE_LINE_LENGTH: int = 200  # 最大引用行长度为200
    MAX_BLOCKQUOTE_LINES: int = 15  # 最大引用行数为15
    MAX_CODE_BLOCK_LENGTH: int = 1500  # 最大代码块内容长度为1500
    MAX_CODE_LANGUAGE_LENGTH: int = 20  # 最大代码语言标识符长度为20
    MAX_INDENTED_CODE_LINES: int = 20  # 最大缩进代码行数为20
    MAX_TABLE_CELL_LENGTH: int = 200  # 最大表格单元格内容长度为200
    MAX_TABLE_ROWS: int = 20  # 最大表格行数为20
    MAX_HTML_TABLE_LENGTH: int = 2000  # 最大HTML表格内容长度为2000
    MIN_HORIZONTAL_RULE_LENGTH: int = 3  # 最小水平分隔线长度为3
    MAX_SENTENCE_LENGTH: int = 400  # 最大句子长度为400
    MAX_QUOTED_TEXT_LENGTH: int = 300  # 最大引用文本长度为300
    MAX_PARENTHETICAL_CONTENT_LENGTH: int = 200  # 最大括号内内容长度为200
    MAX_NESTED_PARENTHESES: int = 5  # 最大嵌套括号数为5
    MAX_MATH_INLINE_LENGTH: int = 100  # 最大行内数学公式长度为100
    MAX_MATH_BLOCK_LENGTH: int = 500  # 最大数学块公式长度为500
    MAX_PARAGRAPH_LENGTH: int = 1000  # 最大段落长度为1000
    MAX_STANDALONE_LINE_LENGTH: int = 800  # 最大独立行长度为800
    MAX_HTML_TAG_ATTRIBUTES_LENGTH: int = 100  # 最大HTML标签属性长度为100
    MAX_HTML_TAG_CONTENT_LENGTH: int = 1000  # 最大HTML标签内容长度为1000
    LOOKAHEAD_RANGE: int = 100  # 向前查找范围为100



class RegexPatterns:
    """正则表达式模式构建器"""
    
    def __init__(self) -> None:
        """初始化正则表达式模式"""
        # 基础模式定义
        self.AVOID_AT_START = r'[\s\]})>,\']'
        self.PUNCTUATION = (
            r'[.!?…]|\.{3}|[\u2026\u2047-\u2049]|'
            r'[\p{Emoji_Presentation}\p{Extended_Pictographic}]'
        )
        self.QUOTE_END = r"(?:'(?=`)|''(?=``))"
        self.SENTENCE_END = (
            f"(?:{self.PUNCTUATION}(?<!{self.AVOID_AT_START}"
            f"(?={self.PUNCTUATION}))|{self.QUOTE_END})(?=\\S|$)"
        )
        self.SENTENCE_BOUNDARY = f"(?:{self.SENTENCE_END}|(?=[\\r\\n]|$))"
        
    def build_sentence_pattern(self, max_length: int) -> str:
        """构建句子匹配模式
        
        Args:
            max_length: 句子的最大长度限制
            
        Returns:
            构建好的正则表达式模式字符串
        """
        lookahead_pattern = (
            f"(?:(?!{self.SENTENCE_END}).)"
            f"{{1,{TextConstants.LOOKAHEAD_RANGE}}}{self.SENTENCE_END}"
        )
        not_punctuation_space = f"(?!{self.PUNCTUATION}\\s)"
        
        return (
            f"{not_punctuation_space}(?:[^\\r\\n]{{1,{max_length}}}"
            f"{self.SENTENCE_BOUNDARY}|[^\\r\\n]{{1,{max_length}}}"
            f"(?={self.PUNCTUATION}|{self.QUOTE_END})"
            f"(?:{lookahead_pattern})?){self.AVOID_AT_START}*"
        )


class TextChunker:
    """文本分块处理器"""
    
    def __init__(self) -> None:
        """初始化文本分块器"""
        self.patterns = RegexPatterns()
        self.regex = self._build_full_regex()
    
    def _build_full_regex(self) -> re.Pattern:
        """构建完整的正则表达式

        构建用于文本分块的完整正则表达式，包含所有可能的文本模式。
        包括标题、列表、引用块、代码块、表格等所有Markdown语法结构。

        Returns:
            编译好的正则表达式对象
        """
        const = TextConstants  # 引用TextConstants类中的常量
        patterns = []  # 用于存储各个正则模式的列表

        # 1. 标题 (Setext风格、Markdown风格和HTML风格)
        patterns.append(
            f"(?:"
            # Markdown-style headers (#, *, =, or -)
            f"^(?:(?:[#*=-]{{1,{const.MAX_HEADING_LENGTH}}})"  # 处理Markdown标题（#，*，=，-）
            f"|(?:\\w[^\\r\\n]{{0,{const.MAX_HEADING_CONTENT_LENGTH}}}\\r?\\n"  # 处理带内容长度的标题
            f"[-=]{{2,{const.MAX_HEADING_UNDERLINE_LENGTH}}})"  # 处理Setext风格下划线
            f"|<h[1-6][^>]*>)"  # 匹配HTML <h1> 到 <h6>，并支持可选属性
            f"[^\\r\\n]{{1,{const.MAX_HEADING_CONTENT_LENGTH}}}"  # 匹配标题内容
            f"(?:</h[1-6]>)?"  # 可选的HTML头部关闭标签
            f"(?:\\r?\\n|$))"  # 允许换行符或字符串结尾
        )

        # 2. 引用标记
        patterns.append(
            f"(?:\\[[0-9]+\\][^\\r\\n]{{1,{const.MAX_STANDALONE_LINE_LENGTH}}})"
        )

        # 3. 列表项 (项目符号、编号、字母或任务列表，包括嵌套)
        sentence_pattern = self.patterns.build_sentence_pattern(const.MAX_LIST_ITEM_LENGTH)  # 构建列表项的句子模式
        patterns.append(
            f"(?:(?:^|\\r?\\n)[ \\t]{{0,3}}(?:[-*+•]|\\d{{1,3}}\\.\\w\\.|\\[[ xX]\\])[ \\t]+{sentence_pattern}"
            f"(?:(?:\\r?\\n[ \\t]{{2,5}}(?:[-*+•]|\\d{{1,3}}\\.\\w\\.|\\[[ xX]\\])[ \\t]+{sentence_pattern})"
            f"{{0,{const.MAX_NESTED_LIST_ITEMS}}}"
            f"(?:\\r?\\n[ \\t]{{4,{const.MAX_LIST_INDENT_SPACES}}}(?:[-*+•]|\\d{{1,3}}\\.\\w\\.|\\[[ xX]\\])[ \\t]+{sentence_pattern})"
            f"{{0,{const.MAX_NESTED_LIST_ITEMS}}})?)"
        )

        # 4. 引用块 (包括嵌套引用和引文)
        sentence_pattern = self.patterns.build_sentence_pattern(const.MAX_BLOCKQUOTE_LINE_LENGTH)  # 构建引用块的句子模式
        patterns.append(
            f"(?:(?:^>(?:>|\\s{{2,}}){{0,2}}{sentence_pattern}\\r?\\n?)"
            f"{{1,{const.MAX_BLOCKQUOTE_LINES}}})"
        )

        # 5. 代码块 (围栏式、缩进式或HTML pre/code标签)
        patterns.append(
            f"(?:(?:^|[\r\n]))"  # 匹配行首或前一个换行符
            # 围栏式代码块（反引号或波浪线）
            f"(?:`{{3}}|~{{3}})"  # 开始标记（3个反引号或波浪线）
            f"(?:\\w{{0,{const.MAX_CODE_LANGUAGE_LENGTH}}})?"  # 可选的语言标识符
            f"\\r?\\n"  # 开始标记后的换行符
            f"[\\s\\S]{{0,{const.MAX_CODE_BLOCK_LENGTH}}}?"  # 匹配代码内容（任意字符）
            f"(?:`{{3}}|~{{3}})"  # 结束标记（3个反引号或波浪线）
            f"\\r?\\n?"  # 结束标记后的可选换行符

            # 缩进式代码块（4个空格或1个制表符）
            f"|(?:^|\\r?\\n)"  # 匹配行首或前一个换行符
            f"(?: {4}|\\t)"  # 匹配4个空格或一个制表符作为缩进
            f"[^\\r\\n]{{0,{const.MAX_LIST_ITEM_LENGTH}}}"  # 匹配缩进的代码行（不超过指定长度）
            f"(?:\\r?\\n(?: {4}|\\t)[^\\r\\n]{{0,{const.MAX_LIST_ITEM_LENGTH}}})"  # 处理多行缩进
            f"{{0,{const.MAX_INDENTED_CODE_LINES}}}"  # 处理最多指定数量的缩进行
            f"\\r?\\n?"  # 可选的结束换行符

            # HTML <pre><code> 代码块
            f"|(?:<pre>(?:<code>)?[\\s\\S]{{0,{const.MAX_CODE_BLOCK_LENGTH}}}?(?:</code>)?</pre>)"  # 匹配HTML格式的代码块
        )

        # 6. 表格 (Markdown表格、网格表格和HTML表格)
        patterns.append(
            f"(?:(?:^|\\r?\\n)(?:\\|[^\\r\\n]{{0,{const.MAX_TABLE_CELL_LENGTH}}}\\|"
            f"(?:\\r?\\n\\|[-:]{{1,{const.MAX_TABLE_CELL_LENGTH}}}\\|){{0,1}}"
            f"(?:\\r?\\n\\|[^\\r\\n]{{0,{const.MAX_TABLE_CELL_LENGTH}}}\\|)"
            f"{{0,{const.MAX_TABLE_ROWS}}}|"
            f"<table>[\\s\\S]{{0,{const.MAX_HTML_TABLE_LENGTH}}}?</table>))"
        )

        # 7. 水平分割线 (Markdown和HTML hr标签)
        patterns.append(
            f"(?:^(?:[-*_]){{{const.MIN_HORIZONTAL_RULE_LENGTH},}}\\s*$|<hr\\s*/?>)"
        )

        # 8. 独立行或短语
        sentence_pattern = self.patterns.build_sentence_pattern(const.MAX_STANDALONE_LINE_LENGTH)  # 构建独立行的句子模式
        patterns.append(
            f"(?!{self.patterns.AVOID_AT_START})(?:^(?:<[a-zA-Z][^>]"
            f"{{0,{const.MAX_HTML_TAG_ATTRIBUTES_LENGTH}}}>)?"
            f"{sentence_pattern}(?:</[a-zA-Z]+>)?(?:\\r?\\n|$))"
        )

        # 9. 带标点的句子或短语
        sentence_pattern = self.patterns.build_sentence_pattern(const.MAX_SENTENCE_LENGTH)  # 构建带标点的句子模式
        patterns.append(
            f"(?!{self.patterns.AVOID_AT_START}){sentence_pattern}"
        )

        # 10. 引用文本、括号内容或方括号内容
        patterns.append(
            f"(?:"
            f"(?<!\\w)\"\"\"[^\"]{{{0,{const.MAX_QUOTED_TEXT_LENGTH}}}}\"\"\"(?!\\w)|"
            f"(?<!\\w)(?:['\"`'""])[^\\r\\n]{{{0,{const.MAX_QUOTED_TEXT_LENGTH}}}}\\1(?!\\w)|"
            f"(?<!\\w)`[^\\r\\n]{{{0,{const.MAX_QUOTED_TEXT_LENGTH}}}}'(?!\\w)|"
            f"(?<!\\w)``[^\\r\\n]{{{0,{const.MAX_QUOTED_TEXT_LENGTH}}}}''(?!\\w)|"
            f"\\([^\\r\\n()]{{{0,{const.MAX_PARENTHETICAL_CONTENT_LENGTH}}}}"
            f"(?:\\([^\\r\\n()]{{{0,{const.MAX_PARENTHETICAL_CONTENT_LENGTH}}}}\\)"
            f"[^\\r\\n()]{{{0,{const.MAX_PARENTHETICAL_CONTENT_LENGTH}}}})"
            f"{{0,{const.MAX_NESTED_PARENTHESES}}}\\)|"
            f"\\[[^\\r\\n\\[\\]]{{{0,{const.MAX_PARENTHETICAL_CONTENT_LENGTH}}}}"
            f"(?:\\[[^\\r\\n\\[\\]]{{{0,{const.MAX_PARENTHETICAL_CONTENT_LENGTH}}}}\\]"
            f"[^\\r\\n\\[\\]]{{{0,{const.MAX_PARENTHETICAL_CONTENT_LENGTH}}}})"
            f"{{0,{const.MAX_NESTED_PARENTHESES}}}\\]|"
            f"\\$[^\\r\\n$]{{{0,{const.MAX_MATH_INLINE_LENGTH}}}}\\$|"
            f"`[^`\\r\\n]{{{0,{const.MAX_MATH_INLINE_LENGTH}}}}`"
            f")"
        )

        # 11. 段落
        sentence_pattern = self.patterns.build_sentence_pattern(const.MAX_PARAGRAPH_LENGTH)  # 构建段落的句子模式
        patterns.append(
            f"(?!{self.patterns.AVOID_AT_START})(?:(?:^|\\r?\\n\\r?\\n)(?:<p>)?"
            f"{sentence_pattern}(?:</p>)?(?=\\r?\\n\\r?\\n|$))"
        )

        # 12. HTML标签及其内容
        patterns.append(
            f"(?:<[a-zA-Z][^>]{{{0,{const.MAX_HTML_TAG_ATTRIBUTES_LENGTH}}}}"
            f"(?:>[\\s\\S]{{{0,{const.MAX_HTML_TAG_CONTENT_LENGTH}}}}?</[a-zA-Z]+>|\\s*/>))"
        )

        # 13. LaTeX风格数学表达式
        patterns.append(
            f"(?:(?:\\$\\$[\\s\\S]{{{0,{const.MAX_MATH_BLOCK_LENGTH}}}}?\\$\\$)|"
            f"(?:\\$[^\\$\\r\\n]{{{0,{const.MAX_MATH_INLINE_LENGTH}}}}\\$))"
        )

        # 14. 后备模式：任何剩余内容
        sentence_pattern = self.patterns.build_sentence_pattern(const.MAX_STANDALONE_LINE_LENGTH)  # 构建剩余内容的句子模式
        patterns.append(
            f"(?!{self.patterns.AVOID_AT_START}){sentence_pattern}"
        )

        # 合并所有模式
        # print(patterns[4])
        # patterns.remove(patterns[4])
        full_pattern = "|".join(f"({pattern})" for pattern in patterns)  # 将所有模式合并为一个完整的正则表达式
        return re.compile(full_pattern, re.MULTILINE | re.UNICODE | re.VERBOSE)  # 编译正则表达式并返回

    def process_file(self, filepath: str) -> List[TextChunk]:
        """处理文本文件
        
        Args:
            filepath: 待处理文件的路径
            
        Returns:
            分块后的文本列表
            
        Raises:
            FileNotFoundError: 文件不存在时抛出
            UnicodeDecodeError: 文件编码错误时抛出
        """
        # 记录开始时间和内存使用
        start_time = time.time()
        start_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"错误：文件 '{filepath}' 不存在")
            return []
        except UnicodeDecodeError:
            print(f"错误：文件 '{filepath}' 编码错误")
            return []
            
        # 进行文本分块
        chunks = []
        for match in self.regex.finditer(content):
            chunk = TextChunk(
                content=match.group(0),
                chunk_type=self._determine_chunk_type(match),
                start_pos=match.start(),
                end_pos=match.end()
            )
            chunks.append(chunk)
            
        # 计算处理时间和内存使用
        end_time = time.time()
        end_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        # 输出统计信息
        self._print_statistics(
            chunks, 
            end_time - start_time,
            end_memory - start_memory
        )
        
        return chunks
    
    def _determine_chunk_type(self, match: re.Match) -> str:
        """确定文本块的类型
        
        Args:
            match: 正则表达式匹配结果
            
        Returns:
            文本块类型的字符串描述
        """
        # 根据匹配的组号确定类型
        for i, group in enumerate(match.groups()):
            if group is not None:
                return f"Type_{i+1}"
        return "Unknown"
    
    def _print_statistics(
        self,
        chunks: List[TextChunk],
        execution_time: float,
        memory_used: int
    ) -> None:
        """打印处理统计信息
        
        Args:
            chunks: 分块结果列表
            execution_time: 执行时间（秒）
            memory_used: 内存使用量（字节）
        """
        print(f"分块数量: {len(chunks)}")
        print(f"执行时间: {execution_time:.3f} 秒")
        print(f"内存使用: {self._format_bytes(memory_used)}")
        
        # 打印前10个分块的预览
        print("\n前10个分块预览:")
        for i, chunk in enumerate(chunks[:10]):
            print(f"{i+1}. [{chunk.chunk_type}] {chunk.content[:50]}...")
    
    @staticmethod
    def _format_bytes(bytes_: int) -> str:
        """格式化字节数为人类可读的形式
        
        Args:
            bytes_: 字节数
            
        Returns:
            格式化后的字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_ < 1024:
                return f"{bytes_:.2f} {unit}"
            bytes_ /= 1024
        return f"{bytes_:.2f} TB"


def main() -> None:
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python tokenizer.py <input_file>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    chunker = TextChunker()
    chunks = chunker.process_file(filepath)
    
    # 输出处理结果
    if chunks:
        print("\n处理完成!")
    else:
        print("\n处理失败或没有找到有效的文本块")


if __name__ == "__main__":
    main()