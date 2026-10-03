"""Tools for searching and reading company files."""

from pathlib import Path

class FileSearchTool:
    name = "file_search"

    def search(self, query: str, root: str = "data"):
        results = []
        for path in Path(root).rglob("*"):
            if path.is_file() and query.lower() in path.name.lower():
                results.append(str(path))
        return results
