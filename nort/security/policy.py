from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit


class Policy:
    def __init__(self, root, domains=()):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir(): raise ValueError("Escolha uma pasta de trabalho.")
        self.domains = {d.strip().lower() for d in domains if d.strip()}

    def path(self, value):
        if not isinstance(value, str) or not value or "\x00" in value:
            raise ValueError("Caminho inválido.")
        # Block Windows alternate data streams and UNC paths even on other hosts.
        if value.startswith(("\\\\", "//")) or ":" in value.replace(":\\", "", 1):
            raise PermissionError("Caminho especial não permitido; use caminhos relativos.")
        p = Path(value)
        target = (self.root / p).resolve()
        try: target.relative_to(self.root)
        except ValueError: raise PermissionError("Arquivo fora da pasta autorizada.")
        if target == self.root: raise PermissionError("Operação exige um arquivo ou subpasta.")
        return target

    def url(self, url):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise PermissionError("Use HTTPS sem credenciais e porta padrão.")
        if parsed.hostname not in self.domains:
            raise PermissionError("Domínio não autorizado nas configurações.")
        return url
