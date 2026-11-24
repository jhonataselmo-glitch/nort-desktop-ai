"""Opt-in real Chromium tests against a controlled HTML fixture, without live sites."""
import os
import pytest
from nort.security.policy import Policy
from nort.tools.browser import BrowserTools

pytestmark=pytest.mark.skipif(os.environ.get('NORT_BROWSER_TESTS')!='1',reason='Set NORT_BROWSER_TESTS=1 with Playwright Chromium installed')


def test_real_browser_fill_click_assert_screenshot(tmp_path):
    browser=BrowserTools(Policy(tmp_path,['example.com']),headless=True)
    try:
        browser.start()
        browser.page.route('https://example.com/**',lambda route:route.fulfill(content_type='text/html',body='''
        <label>Nome<input id="nome"></label><label>Senha<input type="password"></label>
        <button onclick="document.querySelector('#result').innerText='Confirmado'">Continuar</button><p id="result"></p>
        '''))
        browser.open_url('https://example.com/test')
        browser.browser_fill('Nome','Ana')
        assert 'Nome' in browser.browser_read()
        with pytest.raises(PermissionError):browser.browser_fill('Senha','blocked')
        browser.browser_click('button','Continuar')
        assert browser.assert_text('Confirmado')['verified']
        capture=browser.take_screenshot('screen.png')
        assert (tmp_path/'screen.png').read_bytes().startswith(b'\x89PNG')
        with pytest.raises(FileExistsError):browser.take_screenshot('screen.png')
        with pytest.raises(PermissionError):browser.open_url('https://evil.test')
    finally:browser.close()


def test_ambiguous_control_fails_without_click(tmp_path):
    browser=BrowserTools(Policy(tmp_path,['example.com']),headless=True)
    try:
        browser.start()
        browser.page.route('https://example.com/**',lambda route:route.fulfill(content_type='text/html',body='<button>Enviar</button><button>Enviar</button>'))
        browser.open_url('https://example.com/test')
        with pytest.raises(ValueError,match='ambíguo'):browser.browser_click('button','Enviar')
    finally:browser.close()
