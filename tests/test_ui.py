import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from nort.ui.main import MainWindow, Worker
from nort.security.policy import Policy
from nort.security.audit import Audit
from nort.core.models import Plan,Step


def test_ui_constructs_and_worker_copies_real_file(tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'runtime'))
    app=QApplication.instance() or QApplication([])
    window=MainWindow()
    window.root.setText(str(tmp_path))
    assert window.generate.isEnabled() and not window.cancel_button.isEnabled()
    (tmp_path/'source.txt').write_text('worker integration')
    plan=Plan('Copiar',[Step('s1','Copiar','copy_file',{'source':'source.txt','destination':'out.txt'})])
    worker=Worker(Policy(tmp_path),'unused','Test',plan.to_json(),'automatico',Audit(tmp_path/'audit.jsonl'))
    worker.start()
    assert worker.wait(10000)
    app.processEvents()
    assert (tmp_path/'out.txt').read_text()=='worker integration'
    window.close()
