"""
Minimal YAML parser for UCAS.
Supports: dicts, lists (flow/block), strings, booleans, null, comments.
NO support for: multiline strings, anchors, tags, complex scalars.
"""

import re
from typing import Any, Dict, List, Union


class YAMLParseError(Exception):
    """YAML parsing error with line number."""
    def __init__(self, message: str, line_num: int = None):
        self.line_num = line_num
        if line_num:
            super().__init__(f"Line {line_num}: {message}")
        else:
            super().__init__(message)


def parse_yaml(text: str) -> Dict[str, Any]:
    """Parse YAML text into Python dict."""
    parser = YAMLParser(text)
    return parser.parse()


class YAMLParser:
    def __init__(self, text: str):
        self.lines = text.splitlines()
        self.line_idx = 0

    def parse(self) -> Dict[str, Any]:
        """Parse the entire document."""
        result = {}
        while self.line_idx < len(self.lines):
            line = self._current_line()
            if not line or line.startswith('#'):
                self.line_idx += 1
                continue

            # Root level must be dict items
            indent = self._get_indent(line)
            if indent > 0:
                raise YAMLParseError("Root level must have no indentation", self.line_idx + 1)

            key, value = self._parse_dict_item(line, 0)
            result[key] = value
            self.line_idx += 1

        return result

    def _current_line(self) -> str:
        """Get current line, stripped of comments and trailing whitespace."""
        if self.line_idx >= len(self.lines):
            return ""
        line = self.lines[self.line_idx]
        # Remove comments (but not in quoted strings)
        if '#' in line:
            # Simple approach: only strip if # is not in quotes
            in_quote = False
            quote_char = None
            for i, c in enumerate(line):
                if c in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                    if not in_quote:
                        in_quote = True
                        quote_char = c
                    elif c == quote_char:
                        in_quote = False
                elif c == '#' and not in_quote:
                    line = line[:i]
                    break
        return line.rstrip()

    def _get_indent(self, line: str) -> int:
        """Get indentation level (number of spaces)."""
        return len(line) - len(line.lstrip(' '))

    def _parse_dict_item(self, line: str, base_indent: int) -> tuple:
        """Parse a single dict item: 'key: value'."""
        stripped = line.lstrip()

        if ':' not in stripped:
            raise YAMLParseError(f"Expected 'key: value', got: {stripped}", self.line_idx + 1)

        colon_idx = stripped.index(':')
        key = stripped[:colon_idx].strip()
        value_str = stripped[colon_idx + 1:].strip()

        if not key:
            raise YAMLParseError("Empty key", self.line_idx + 1)

        # Parse value
        if not value_str:
            # Value on next lines (nested dict or list)
            value = self._parse_nested(base_indent)
        elif value_str == '|':
            # Multiline string
            value = self._parse_multiline_string(base_indent)
        elif value_str.startswith('['):
            # Flow list
            value = self._parse_flow_list(value_str)
        elif value_str.startswith('{'):
            # Flow dict
            value = self._parse_flow_dict(value_str)
        else:
            # Scalar value
            value = self._parse_scalar(value_str)

        return key, value

    def _parse_nested(self, parent_indent: int) -> Union[Dict, List]:
        """Parse nested structure (dict or list)."""
        # Peek at next line
        self.line_idx += 1
        if self.line_idx >= len(self.lines):
            return None

        next_line = self._current_line()
        while not next_line and self.line_idx < len(self.lines):
            self.line_idx += 1
            next_line = self._current_line()

        if not next_line:
            return None

        next_indent = self._get_indent(next_line)
        if next_indent <= parent_indent:
            # No nested content
            self.line_idx -= 1
            return None

        # Check if it's a list (starts with -)
        if next_line.lstrip().startswith('-'):
            return self._parse_block_list(next_indent)
        else:
            return self._parse_block_dict(next_indent)

    def _parse_block_dict(self, base_indent: int) -> Dict[str, Any]:
        """Parse a block-style dict."""
        result = {}

        while self.line_idx < len(self.lines):
            line = self._current_line()
            if not line:
                self.line_idx += 1
                continue

            indent = self._get_indent(line)
            if indent < base_indent:
                # Back to parent level
                self.line_idx -= 1
                break
            elif indent > base_indent:
                raise YAMLParseError(f"Unexpected indentation", self.line_idx + 1)

            key, value = self._parse_dict_item(line, base_indent)
            result[key] = value
            self.line_idx += 1

        return result

    def _parse_block_list(self, base_indent: int) -> List[Any]:
        """Parse a block-style list."""
        result = []

        while self.line_idx < len(self.lines):
            line = self._current_line()
            if not line:
                self.line_idx += 1
                continue

            indent = self._get_indent(line)
            if indent < base_indent:
                # Back to parent level
                self.line_idx -= 1
                break
            elif indent > base_indent:
                raise YAMLParseError(f"Unexpected indentation", self.line_idx + 1)

            stripped = line.lstrip()
            if not stripped.startswith('-'):
                raise YAMLParseError(f"Expected list item (starting with -), got: {stripped}", self.line_idx + 1)

            value_str = stripped[1:].strip()

            if not value_str:
                # Value on next line
                value = self._parse_nested(base_indent)
            elif value_str.startswith('['):
                value = self._parse_flow_list(value_str)
            elif value_str.startswith('{'):
                value = self._parse_flow_dict(value_str)
            else:
                value = self._parse_scalar(value_str)

            result.append(value)
            self.line_idx += 1

        return result

    def _parse_multiline_string(self, parent_indent: int) -> str:
        """Parse a multiline string starting with |."""
        self.line_idx += 1
        lines = []
        base_indent = -1

        while self.line_idx < len(self.lines):
            line = self.lines[self.line_idx]
            
            # Skip empty lines
            if not line.strip():
                lines.append("")
                self.line_idx += 1
                continue
                
            indent = self._get_indent(line)
            if indent <= parent_indent:
                # Back to parent level
                self.line_idx -= 1
                break
            
            if base_indent == -1:
                base_indent = indent
            
            # Add line stripped of base indentation
            lines.append(line[base_indent:])
            self.line_idx += 1
            
        # Join lines and rstrip to remove extra newlines at end
        return "\n".join(lines).rstrip()

    def _parse_flow_list(self, text: str) -> List[Any]:
        """Parse flow-style list: [a, b, c]."""
        if not text.endswith(']'):
            raise YAMLParseError(f"Flow list must end with ], got: {text}", self.line_idx + 1)

        inner = text[1:-1].strip()
        if not inner:
            return []

        # Simple split by comma (doesn't handle nested structures)
        items = []
        current = ""
        depth = 0
        in_quote = False
        quote_char = None

        for c in inner:
            if c in ('"', "'") and not in_quote:
                in_quote = True
                quote_char = c
                current += c
            elif c == quote_char and in_quote:
                in_quote = False
                current += c
            elif c in ('[', '{') and not in_quote:
                depth += 1
                current += c
            elif c in (']', '}') and not in_quote:
                depth -= 1
                current += c
            elif c == ',' and depth == 0 and not in_quote:
                items.append(self._parse_scalar(current.strip()))
                current = ""
            else:
                current += c

        if current.strip():
            items.append(self._parse_scalar(current.strip()))

        return items

    def _parse_flow_dict(self, text: str) -> Dict[str, Any]:
        """Parse flow-style dict: {key: value, ...}."""
        if not text.endswith('}'):
            raise YAMLParseError(f"Flow dict must end with }}, got: {text}", self.line_idx + 1)

        inner = text[1:-1].strip()
        if not inner:
            return {}

        result = {}
        # Split by comma at top level
        items = []
        current = ""
        depth = 0
        in_quote = False
        quote_char = None

        for c in inner:
            if c in ('"', "'") and not in_quote:
                in_quote = True
                quote_char = c
                current += c
            elif c == quote_char and in_quote:
                in_quote = False
                current += c
            elif c in ('[', '{') and not in_quote:
                depth += 1
                current += c
            elif c in (']', '}') and not in_quote:
                depth -= 1
                current += c
            elif c == ',' and depth == 0 and not in_quote:
                items.append(current.strip())
                current = ""
            else:
                current += c

        if current.strip():
            items.append(current.strip())

        # Parse each key: value pair
        for item in items:
            if ':' not in item:
                raise YAMLParseError(f"Flow dict item must be 'key: value', got: {item}", self.line_idx + 1)
            k, v = item.split(':', 1)
            result[k.strip()] = self._parse_scalar(v.strip())

        return result

    def _parse_scalar(self, text: str) -> Any:
        """Parse a scalar value (string, bool, null, number)."""
        text = text.strip()

        if not text:
            return None

        # Boolean
        if text in ('true', 'True', 'TRUE'):
            return True
        if text in ('false', 'False', 'FALSE'):
            return False

        # Null
        if text in ('null', 'Null', 'NULL', '~'):
            return None

        # Quoted string
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            return text[1:-1]

        # Number
        if re.match(r'^-?\d+$', text):
            return int(text)
        if re.match(r'^-?\d+\.\d+$', text):
            return float(text)

        # Unquoted string
        return text
