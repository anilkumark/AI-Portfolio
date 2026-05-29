
import os
from pathlib import Path
import glob

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("file-system-server")

@mcp.tool()
def read_file(file_path: str) -> str:
    """Read contents of a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def write_file(file_path: str, content: str) -> str:
    """Write content to a file"""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Written {len(content)} characters to {file_path}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def list_directory(directory_path: str = ".") -> str:
    """List contents of a directory"""
    try:
        path = Path(directory_path)
        if not path.exists():
            return f"Directory not found: {directory_path}"
        
        items = []
        for item in sorted(path.iterdir()):
            item_type = "DIR" if item.is_dir() else "FILE"
            items.append(f"{item_type} {item.name}")
        
        return "\n".join(items)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.resource("research://files")
def list_research_files():
    """List all research files saved by the AI assistant"""
    try:
        research_files = glob.glob("research_*.txt")
        return [f"research://files/{file}" for file in research_files]
    except Exception:
        return []

@mcp.resource("research://files/{filename}")
def get_research_file(filename: str):
    """Get content of a specific research file"""
    try:
        if not filename.startswith("research_") or not filename.endswith(".txt"):
            return None
        
        if not os.path.exists(filename):
            return None
            
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return content
    except Exception:
        return None


if __name__ == "__main__":
    mcp.run(transport="stdio")