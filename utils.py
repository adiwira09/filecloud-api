def format_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_in_bytes / (1024 * 1024 * 1024):.1f} GB"

def get_file_type(filename: str) -> str:
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in ["pdf"]:
        return "pdf"
    elif ext in ["doc", "docx"]:
        return "doc"
    elif ext in ["txt"]:
        return "text"
    elif ext in ["jpg", "jpeg", "png", "gif", "webp"]:
        return "image"
    elif ext in ["ppt", "pptx"]:
        return "ppt"
    elif ext in ["mp4", "webm", "mkv", "avi"]:
        return "video"
    elif ext in ["mp3", "wav", "ogg", "flac"]:
        return "audio"
    return "other"
