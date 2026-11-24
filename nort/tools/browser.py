class BrowserTools:
    def __init__(self, policy, headless=False):
        self.policy=policy
        self.headless=headless
        self.pw=self.browser=self.page=None

    def start(self):
        if self.pw: return
        from playwright.sync_api import sync_playwright
        self.pw=sync_playwright().start()
        # Uses Edge already installed on Windows, falling back to installed Playwright Chromium.
        import sys
        try: self.browser=self.pw.chromium.launch(headless=self.headless, channel="msedge" if sys.platform=="win32" else None)
        except Exception: self.browser=self.pw.chromium.launch(headless=self.headless)
        self.context=self.browser.new_context(accept_downloads=False, service_workers="block")
        self.context.route("**/*", self.route)
        self.context.route_web_socket("**/*", lambda ws: ws.close())
        self.page=self.context.new_page()
        self.page.set_default_timeout(10000)
        self.page.set_default_navigation_timeout(20000)

    def route(self, route):
        # HTTP(S) request allowlist; service workers and WebSockets are disabled.
        try: self.policy.url(route.request.url)
        except Exception: route.abort(); return
        route.continue_()

    def current(self):
        if not self.page: raise ValueError("Abra o navegador primeiro.")
        self.policy.url(self.page.url)
        return self.page

    def open_url(self, url):
        """Abre URL HTTPS em domínio autorizado, em navegador isolado. Login manual."""
        self.policy.url(url)
        self.start()
        self.page.goto(url, wait_until="domcontentloaded")
        self.current()
        return {"url":self.page.url,"title":self.page.title()}

    def browser_read(self):
        """Lê texto visível (até 12000 caracteres). Resultado local, não enviado à IA."""
        return self.current().locator("body").inner_text()[:12000]

    def browser_click(self, role, name):
        """Clica elemento único por role e nome acessível EXATO. Sempre exige confirmação."""
        loc=self.current().get_by_role(role,name=name,exact=True)
        if loc.count()!=1: raise ValueError("Elemento ausente ou ambíguo. Inspecione a tela e edite o plano.")
        loc.click()
        return {"action":"click", "name":name}

    def browser_fill(self, label, text):
        """Preenche campo único por label EXATO; não preenche senhas. Exige confirmação."""
        loc=self.current().get_by_label(label,exact=True)
        if loc.count()!=1: raise ValueError("Campo ausente ou ambíguo.")
        if loc.get_attribute("type")=="password": raise PermissionError("Faça login manualmente; senhas não pertencem ao plano.")
        loc.fill(str(text))
        if loc.input_value()!=str(text): raise RuntimeError("Preenchimento não confirmado.")
        return {"filled":label}

    def assert_text(self, text):
        """Confere que texto está visível na página."""
        from playwright.sync_api import expect
        expect(self.current().get_by_text(text,exact=False).first).to_be_visible()
        return {"verified":True}

    def take_screenshot(self, path):
        """Salva captura PNG do navegador na pasta autorizada, sem sobrescrever."""
        p=self.policy.path(path)
        if p.suffix.lower()!=".png": raise ValueError("Use PNG.")
        data=self.current().screenshot()
        with p.open("xb") as f: f.write(data)
        return {"screenshot":str(p)}

    def close(self):
        try:
            if self.browser: self.browser.close()
        finally:
            if self.pw: self.pw.stop()
