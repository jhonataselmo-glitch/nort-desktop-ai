import os
import sys

SERVICE = "NORT Desktop AI"


def secure_backend():
    import keyring
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring
        return WinVaultKeyring()
    if sys.platform == "darwin":
        from keyring.backends.macOS import Keyring
        return Keyring()
    raise RuntimeError("Cofre suportado em Windows/macOS. Use GROQ_API_KEY no ambiente em Linux.")


def get_key():
    value = os.environ.get("GROQ_API_KEY", "").strip()
    if value: return value
    return secure_backend().get_password(SERVICE, "groq") or ""


def save_key(value):
    if not value.strip(): raise ValueError("Chave vazia.")
    secure_backend().set_password(SERVICE, "groq", value.strip())
