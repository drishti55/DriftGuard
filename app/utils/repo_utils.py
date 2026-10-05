from urllib.parse import urlparse

def normalize_repository_name(repo_str: str) -> str:
    """
    Normalizes a repository string into a canonical 'owner/repo' format.
    Handles:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - github.com/owner/repo
    - owner/repo
    - /workspace/owner/repo
    """
    if not repo_str:
        return ""
    
    repo_str = repo_str.strip()
    
    # Handle full URLs
    if repo_str.startswith("http://") or repo_str.startswith("https://"):
        parsed = urlparse(repo_str)
        path = parsed.path
        if path.startswith("/"):
            path = path[1:]
        if path.endswith(".git"):
            path = path[:-4]
        
        parts = path.split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
            
    # Handle github.com/owner/repo
    if repo_str.startswith("github.com/"):
        path = repo_str[len("github.com/"):]
        if path.endswith(".git"):
            path = path[:-4]
        parts = path.split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
            
    # Handle local paths or raw owner/repo
    # E.g. /workspace/owner/repo or owner/repo
    parts = repo_str.split("/")
    
    # Remove empty parts
    parts = [p for p in parts if p]
    
    if len(parts) >= 2:
        # If it's a deep path, assume the last two parts are owner/repo if they don't look like file extensions
        return f"{parts[-2]}/{parts[-1]}"
    elif len(parts) == 1:
        return parts[0]
        
    return repo_str
