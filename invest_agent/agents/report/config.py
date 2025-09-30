from dataclasses import dataclass
from typing import Optional

@dataclass
class ReportConfig:
    version: str = "v1.0"
    author: str = "투자팀"
    target_equity: str = "10–12%"
    check_size: str = "$5–7M"
    renderer: str = "playwright"   # "pdfkit" | "playwright" | "none"
    wkhtmltopdf_path: Optional[str] = None
    out_dir: str = "."
