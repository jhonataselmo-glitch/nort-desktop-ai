import sys


class WindowsTools:
    def __init__(self): self.app=None

    def open_application(self, name):
        """Abre aplicativo Windows permitido: notepad, calculator, excel ou word. Sem argumentos."""
        if sys.platform!="win32": raise RuntimeError("Controle desktop disponível somente no Windows.")
        allowed={"notepad":"notepad.exe", "calculator":"calc.exe", "excel":"excel.exe", "word":"winword.exe"}
        if name not in allowed: raise PermissionError("Aplicativo não autorizado.")
        from pywinauto import Application
        self.app=Application(backend="uia").start(allowed[name])
        return {"application":name, "pid":self.app.process}

    def read_screen(self):
        """Lê controles UI Automation do aplicativo aberto por esta execução."""
        if not self.app: raise ValueError("Abra um aplicativo primeiro.")
        controls=self.app.top_window().descendants()
        return [{"name":c.element_info.name,"type":c.element_info.control_type,"automation_id":c.element_info.automation_id} for c in controls[:150]]

    def windows_click(self, automation_id, control_type):
        """Clica controle único por Automation ID e tipo dentro do aplicativo aberto."""
        if not self.app: raise ValueError("Abra um aplicativo primeiro.")
        control=self.app.top_window().child_window(auto_id=automation_id, control_type=control_type)
        control.wait("visible enabled", timeout=10)
        control.wrapper_object().click_input()
        return {"clicked":automation_id}
