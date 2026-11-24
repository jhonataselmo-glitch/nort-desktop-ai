import hashlib
import shutil


class FileTools:
    def __init__(self, policy): self.policy=policy

    def list_files(self, subfolder="."):
        """Lista até 500 arquivos da pasta autorizada, sem recursão."""
        p=self.policy.root if subfolder == "." else self.policy.path(subfolder)
        result=[]
        for item in sorted(p.iterdir()):
            if not item.is_symlink() and item.is_file():
                result.append(str(item.relative_to(self.policy.root)))
                if len(result)==500: break
        return result

    def copy_file(self, source, destination):
        """Copia arquivo sem sobrescrever e verifica SHA256. Destino deve ter pasta existente."""
        src,dst=self.policy.path(source),self.policy.path(destination)
        if not src.is_file(): raise ValueError("Origem não é arquivo.")
        if src.stat().st_size > 100_000_000: raise ValueError("Limite de cópia: 100 MB.")
        with src.open("rb") as i, dst.open("xb") as o: shutil.copyfileobj(i,o)
        if self.digest(src)!=self.digest(dst): raise RuntimeError("Cópia não passou na verificação.")
        return {"path":str(dst), "sha256":self.digest(dst)}

    def move_file(self, source, destination):
        """Move/renomeia arquivo: copia, verifica conteúdo e remove origem. Exige confirmação vermelha."""
        result=self.copy_file(source,destination)
        self.policy.path(source).unlink()
        return result

    def assert_file(self, path):
        """Verifica existência, tamanho não zero e SHA256 do arquivo."""
        p=self.policy.path(path)
        if not p.is_file() or p.stat().st_size==0: raise ValueError("Arquivo ausente ou vazio.")
        if p.stat().st_size > 100_000_000: raise ValueError("Verificação limitada a 100 MB.")
        return {"path":str(p), "bytes":p.stat().st_size, "sha256":self.digest(p)}

    @staticmethod
    def digest(path):
        h=hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
        return h.hexdigest()
