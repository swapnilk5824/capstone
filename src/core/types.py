from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class Finding:
    file: str
    severity: str  # blocker | major | minor | info
    category: str  # security | style | logic | testing | docs
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None
    agent: str = ""

    def to_dict(self):
        return asdict(self)


SEVERITY_ORDER = {"blocker": 0, "major": 1, "minor": 2, "info": 3}
