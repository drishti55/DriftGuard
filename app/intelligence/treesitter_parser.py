"""
DriftGuard Universal Tree-sitter Code Intelligence Engine.
Provides universal, zero-cost AST parsing and concrete syntax tree queries
across Python, TypeScript, TSX, JavaScript, and Go.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import tree_sitter
import tree_sitter_go as tsgo
import tree_sitter_javascript as tsjs
import tree_sitter_python as tspython
import tree_sitter_typescript as tstypescript

logger = logging.getLogger(__name__)


@dataclass
class ASTSymbol:
    """Represents a symbol (function, class, method, import) extracted via Tree-sitter."""
    name: str
    kind: str  # 'function', 'class', 'method', 'import', 'call', 'interface', 'type'
    file_path: str
    start_line: int  # 1-indexed
    end_line: int    # 1-indexed
    start_byte: int
    end_byte: int
    signature: str = ""
    parent_symbol: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "signature": self.signature,
            "parent_symbol": self.parent_symbol,
        }


@dataclass
class ParsedASTFile:
    """Represents the complete parsed AST representation of a source file."""
    file_path: str
    language: str
    symbols: List[ASTSymbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)

    def get_symbol_at_line(self, line: int) -> Optional[ASTSymbol]:
        """Finds the most specific AST symbol enclosing a given 1-indexed line."""
        matching = [s for s in self.symbols if s.start_line <= line <= s.end_line]
        if not matching:
            return None
        # Return the symbol with the smallest span (most specific)
        matching.sort(key=lambda s: (s.end_line - s.start_line))
        return matching[0]

    def get_symbols_in_lines(self, lines: Set[int]) -> List[ASTSymbol]:
        """Finds all distinct symbols intersecting with a set of modified lines."""
        result = []
        seen = set()
        for line in lines:
            sym = self.get_symbol_at_line(line)
            if sym and sym.name not in seen:
                seen.add(sym.name)
                result.append(sym)
        return result


class TreeSitterEngine:
    """
    Universal Tree-sitter parser supporting Python, TypeScript, TSX, JS, and Go.
    Extracts structural code artifacts without requiring runtime execution or paid APIs.
    """

    EXT_TO_LANG = {
        ".py": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".go": "go",
    }

    def __init__(self):
        self._parsers: Dict[str, tree_sitter.Parser] = {}
        self._languages: Dict[str, tree_sitter.Language] = {}
        self._init_languages()

    def _init_languages(self):
        try:
            self._languages["python"] = tree_sitter.Language(tspython.language())
            self._parsers["python"] = tree_sitter.Parser(self._languages["python"])

            self._languages["javascript"] = tree_sitter.Language(tsjs.language())
            self._parsers["javascript"] = tree_sitter.Parser(self._languages["javascript"])

            self._languages["typescript"] = tree_sitter.Language(tstypescript.language_typescript())
            self._parsers["typescript"] = tree_sitter.Parser(self._languages["typescript"])

            self._languages["tsx"] = tree_sitter.Language(tstypescript.language_tsx())
            self._parsers["tsx"] = tree_sitter.Parser(self._languages["tsx"])

            self._languages["go"] = tree_sitter.Language(tsgo.language())
            self._parsers["go"] = tree_sitter.Parser(self._languages["go"])
        except Exception as e:
            logger.error(f"Failed to initialize one or more Tree-sitter grammars: {e}")

    def supports_file(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.EXT_TO_LANG

    def get_language_for_file(self, file_path: Path) -> Optional[str]:
        return self.EXT_TO_LANG.get(file_path.suffix.lower())

    def parse_file(self, file_path: Path, content: Optional[str] = None) -> ParsedASTFile:
        """
        Parses a file and returns structured AST symbols, imports, and calls.
        Uses Python's standard library `ast` for Python files for maximum speed and rock-solid stability.
        Uses Tree-sitter for TypeScript, TSX, JavaScript, and Go.
        """
        lang = self.get_language_for_file(file_path)
        if not lang:
            return ParsedASTFile(file_path=str(file_path), language="unsupported")

        if content is None:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
                content = ""

        lines = content.splitlines()
        parsed = ParsedASTFile(
            file_path=str(file_path),
            language=lang,
            raw_lines=lines,
        )

        if lang == "python":
            self._parse_python_ast(content, parsed)
            return parsed

        if lang not in self._parsers:
            return parsed

        content_bytes = content.encode("utf-8")
        parser = self._parsers[lang]
        tree = parser.parse(content_bytes)
        self._walk_and_extract(tree.root_node, parsed, content_bytes, lang)
        return parsed

    def _parse_python_ast(self, content: str, parsed: ParsedASTFile):
        """Extracts AST symbols, imports, and calls for Python using standard library ast."""
        import ast

        try:
            tree = ast.parse(content)
        except SyntaxError:
            if "python" in self._parsers:
                content_bytes = content.encode("utf-8")
                tree_ts = self._parsers["python"].parse(content_bytes)
                self._walk_and_extract(tree_ts.root_node, parsed, content_bytes, "python")
            return

        lines = parsed.raw_lines

        def walk(node: ast.AST, current_parent: Optional[str] = None):
            next_parent = current_parent
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sig_line = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
                parsed.symbols.append(ASTSymbol(
                    name=node.name,
                    kind="method" if current_parent else "function",
                    file_path=parsed.file_path,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    start_byte=getattr(node, "col_offset", 0),
                    end_byte=getattr(node, "end_col_offset", 0),
                    signature=sig_line.strip(),
                    parent_symbol=current_parent,
                ))
                next_parent = node.name
            elif isinstance(node, ast.ClassDef):
                sig_line = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
                parsed.symbols.append(ASTSymbol(
                    name=node.name,
                    kind="class",
                    file_path=parsed.file_path,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    start_byte=getattr(node, "col_offset", 0),
                    end_byte=getattr(node, "end_col_offset", 0),
                    signature=sig_line.strip(),
                    parent_symbol=current_parent,
                ))
                next_parent = node.name
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parsed.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                names = ", ".join(a.name for a in node.names)
                parsed.imports.append(f"from {mod} import {names}")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    parsed.calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    parsed.calls.append(node.func.attr)

            for child in ast.iter_child_nodes(node):
                walk(child, next_parent)

        walk(tree)

    def _walk_and_extract(
        self,
        node: tree_sitter.Node,
        parsed: ParsedASTFile,
        content_bytes: bytes,
        lang: str,
        current_parent: Optional[str] = None,
    ):
        """Recursively walks the AST to discover symbols, imports, and invocations."""
        ntype = node.type
        parent_for_children = current_parent

        # 1. Python Grammar Extractions
        if lang == "python":
            if ntype in ("function_definition", "async_function_definition"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                    sig_line = parsed.raw_lines[node.start_point.row] if node.start_point.row < len(parsed.raw_lines) else ""
                    kind = "method" if current_parent else "function"
                    parsed.symbols.append(ASTSymbol(
                        name=name,
                        kind=kind,
                        file_path=parsed.file_path,
                        start_line=node.start_point.row + 1,
                        end_line=node.end_point.row + 1,
                        start_byte=node.start_byte,
                        end_byte=node.end_byte,
                        signature=sig_line.strip(),
                        parent_symbol=current_parent,
                    ))
                    parent_for_children = name
            elif ntype == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                    sig_line = parsed.raw_lines[node.start_point.row] if node.start_point.row < len(parsed.raw_lines) else ""
                    parsed.symbols.append(ASTSymbol(
                        name=name,
                        kind="class",
                        file_path=parsed.file_path,
                        start_line=node.start_point.row + 1,
                        end_line=node.end_point.row + 1,
                        start_byte=node.start_byte,
                        end_byte=node.end_byte,
                        signature=sig_line.strip(),
                    ))
                    parent_for_children = name
            elif ntype in ("import_statement", "import_from_statement"):
                raw_text = content_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                parsed.imports.append(raw_text.strip())
            elif ntype == "call":
                func_node = node.child_by_field_name("function")
                if func_node:
                    func_name = content_bytes[func_node.start_byte:func_node.end_byte].decode("utf-8", errors="replace")
                    parsed.calls.append(func_name.strip())

        # 2. JavaScript / TypeScript / TSX Grammar Extractions
        elif lang in ("javascript", "typescript", "tsx"):
            if ntype in ("function_declaration", "method_definition", "arrow_function"):
                name_node = node.child_by_field_name("name")
                # Arrow function assigned to variable
                if not name_node and node.parent and node.parent.type == "variable_declarator":
                    name_node = node.parent.child_by_field_name("name")
                if name_node:
                    name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                    sig_line = parsed.raw_lines[node.start_point.row] if node.start_point.row < len(parsed.raw_lines) else ""
                    kind = "method" if current_parent else "function"
                    parsed.symbols.append(ASTSymbol(
                        name=name,
                        kind=kind,
                        file_path=parsed.file_path,
                        start_line=node.start_point.row + 1,
                        end_line=node.end_point.row + 1,
                        start_byte=node.start_byte,
                        end_byte=node.end_byte,
                        signature=sig_line.strip(),
                        parent_symbol=current_parent,
                    ))
                    parent_for_children = name
            elif ntype in ("class_declaration", "interface_declaration", "type_alias_declaration"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                    sig_line = parsed.raw_lines[node.start_point.row] if node.start_point.row < len(parsed.raw_lines) else ""
                    parsed.symbols.append(ASTSymbol(
                        name=name,
                        kind="class" if "class" in ntype else "type",
                        file_path=parsed.file_path,
                        start_line=node.start_point.row + 1,
                        end_line=node.end_point.row + 1,
                        start_byte=node.start_byte,
                        end_byte=node.end_byte,
                        signature=sig_line.strip(),
                    ))
                    parent_for_children = name
            elif ntype == "import_statement":
                raw_text = content_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                parsed.imports.append(raw_text.strip())
            elif ntype == "call_expression":
                func_node = node.child_by_field_name("function")
                if func_node:
                    func_name = content_bytes[func_node.start_byte:func_node.end_byte].decode("utf-8", errors="replace")
                    parsed.calls.append(func_name.strip())

        # 3. Go Grammar Extractions
        elif lang == "go":
            if ntype in ("function_declaration", "method_declaration"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                    sig_line = parsed.raw_lines[node.start_point.row] if node.start_point.row < len(parsed.raw_lines) else ""
                    parsed.symbols.append(ASTSymbol(
                        name=name,
                        kind="function" if ntype == "function_declaration" else "method",
                        file_path=parsed.file_path,
                        start_line=node.start_point.row + 1,
                        end_line=node.end_point.row + 1,
                        start_byte=node.start_byte,
                        end_byte=node.end_byte,
                        signature=sig_line.strip(),
                        parent_symbol=current_parent,
                    ))
                    parent_for_children = name
            elif ntype == "type_declaration":
                # Go type spec
                for child in node.children:
                    if child.type == "type_spec":
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            name = content_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                            sig_line = parsed.raw_lines[node.start_point.row] if node.start_point.row < len(parsed.raw_lines) else ""
                            parsed.symbols.append(ASTSymbol(
                                name=name,
                                kind="class",
                                file_path=parsed.file_path,
                                start_line=node.start_point.row + 1,
                                end_line=node.end_point.row + 1,
                                start_byte=node.start_byte,
                                end_byte=node.end_byte,
                                signature=sig_line.strip(),
                            ))
                            parent_for_children = name
            elif ntype == "import_declaration":
                raw_text = content_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                parsed.imports.append(raw_text.strip())
            elif ntype == "call_expression":
                func_node = node.child_by_field_name("function")
                if func_node:
                    func_name = content_bytes[func_node.start_byte:func_node.end_byte].decode("utf-8", errors="replace")
                    parsed.calls.append(func_name.strip())

        # Recurse children
        for child in node.children:
            self._walk_and_extract(child, parsed, content_bytes, lang, parent_for_children)
