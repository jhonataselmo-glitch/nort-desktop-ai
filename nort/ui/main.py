import json
import os
import threading
import time
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QPlainTextEdit, QLineEdit, QComboBox, QFileDialog, QMessageBox,
    QDialog, QFormLayout, QDialogButtonBox, QSplitter, QInputDialog)
from nort.core.models import Plan
from nort.core.executor import Executor
from nort.agents.planner import GroqPlanner
from nort.security.policy import Policy
from nort.security.audit import Audit
from nort.security.credentials import get_key, save_key
from nort.tools.registry import registry


def app_data():
    p=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local"/"share")))/"NortDesktopAI"
    p.mkdir(parents=True,exist_ok=True)
    return p


class Worker(QThread):
    event=Signal(str,object)
    approval=Signal(object)
    def __init__(self, policy, model, command, plan_text, mode, audit, key=""):
        super().__init__()
        self.policy,self.model,self.command=policy,model,command
        self.plan_text,self.mode,self.audit,self.key=plan_text,mode,audit,key
        self.answer=threading.Event()
        self.decision=False
        self.executor=None
        self.stop=threading.Event()

    def confirm(self,step,tool,args):
        self.answer.clear()
        self.decision=False
        self.approval.emit({"description":step.description,"tool":tool.name,"risk":tool.risk,"args":args})
        while not self.answer.wait(0.1):
            if self.stop.is_set(): return False
        return self.decision and not self.stop.is_set()

    def cancel(self):
        self.stop.set()
        if self.executor: self.executor.cancel()
        self.answer.set()

    def run(self):
        tools,browser=registry(self.policy)
        try:
            if self.plan_text is None:
                plan=GroqPlanner(self.key,self.model).create(self.command,tools)
                if not self.stop.is_set(): self.event.emit("plan",plan.to_json())
            else:
                plan=Plan.parse(self.plan_text,tools)
                self.executor=Executor(tools,self.audit,self.confirm,self.event.emit)
                if self.stop.is_set(): self.executor.cancel()
                self.executor.run(plan,self.mode,self.command)
        except Exception as e:
            if not self.stop.is_set(): self.event.emit("error",str(e))
        finally:
            self.key=""
            try: browser.close()
            except Exception: pass


class Settings(QDialog):
    def __init__(self,parent,config):
        super().__init__(parent)
        self.setWindowTitle("Configurações • Groq e permissões")
        self.resize(620,300)
        layout=QFormLayout(self)
        self.model=QLineEdit(config.get("model","openai/gpt-oss-120b"))
        self.domains=QLineEdit(config.get("domains",""))
        self.domains.setPlaceholderText("exemplo.com, login.exemplo.com")
        self.key=QLineEdit();self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("Deixe vazio para manter a chave atual")
        layout.addRow("Modelo Groq",self.model)
        layout.addRow("Domínios HTTPS autorizados",self.domains)
        layout.addRow("Chave Groq (cofre do sistema)",self.key)
        note=QLabel("O comando e o catálogo de ferramentas são enviados à Groq.\nPlanilhas, páginas e capturas permanecem locais neste MVP.\nNão inclua senhas ou dados pessoais no comando.\nPlano gratuito sujeito aos limites da sua conta.")
        note.setWordWrap(True);layout.addRow(note)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NORT DESKTOP AI • MVP 0.1")
        self.resize(1200,840)
        self.data=app_data(); self.worker=None; self.started=0; self.paused=False
        try: self.config=json.loads((self.data/"config.json").read_text(encoding="utf-8"))
        except (OSError,ValueError): self.config={}
        self.audit=Audit(self.data/"logs"/"audit.jsonl")
        self.library=self.data/"automations";self.library.mkdir(exist_ok=True)
        central=QWidget(); self.setCentralWidget(central)
        main=QVBoxLayout(central);main.setContentsMargins(28,22,28,22);main.setSpacing(12)
        top=QHBoxLayout();brand=QLabel("NORT  <span style='color:#58dbb7'>DESKTOP AI</span>")
        brand.setStyleSheet("font-size:26px;font-weight:700")
        top.addWidget(brand);top.addStretch()
        self.settings_button=QPushButton("Configurações");self.settings_button.clicked.connect(self.settings)
        top.addWidget(self.settings_button);main.addLayout(top)
        subtitle=QLabel("Automação Windows com plano revisável, ferramentas reais e controle humano.")
        subtitle.setStyleSheet("color:#a5b5c8");main.addWidget(subtitle)
        row=QHBoxLayout();self.root=QLineEdit(self.config.get("root",""));self.root.setPlaceholderText("Selecione a pasta autorizada para arquivos e planilhas")
        self.browse=QPushButton("Escolher pasta");self.browse.clicked.connect(self.choose_folder)
        self.mode=QComboBox();self.mode.addItem("Assistido • aprovar cada etapa","assistido");self.mode.addItem("Automático • plano aprovado + confirmações sensíveis","automatico")
        row.addWidget(self.root,3);row.addWidget(self.browse);row.addWidget(self.mode,2);main.addLayout(row)
        main.addWidget(QLabel("O QUE VOCÊ DESEJA AUTOMATIZAR?"))
        self.command=QPlainTextEdit();self.command.setPlaceholderText('Leia admissoes.xlsx, filtre a coluna admissao pelo mês 2026-09 e salve em admissoes_setembro.xlsx.')
        self.command.setMaximumHeight(100);main.addWidget(self.command)
        actions=QHBoxLayout()
        self.generate=QPushButton("EXECUTAR • GERAR PLANO");self.generate.setObjectName("primary");self.generate.clicked.connect(self.create_plan)
        self.load=QPushButton("Minhas automações");self.load.clicked.connect(self.load_plan)
        self.save=QPushButton("Salvar automação");self.save.clicked.connect(self.save_plan)
        actions.addWidget(self.generate);actions.addStretch();actions.addWidget(self.load);actions.addWidget(self.save);main.addLayout(actions)
        split=QSplitter(Qt.Horizontal)
        left=QWidget();ll=QVBoxLayout(left);ll.setContentsMargins(0,0,10,0)
        ll.addWidget(QLabel("PLANO DA IA • JSON EDITÁVEL"))
        self.plan=QPlainTextEdit();self.plan.setPlaceholderText("O plano aparecerá aqui. Revise as ferramentas e argumentos antes de aprovar.");ll.addWidget(self.plan)
        self.approve=QPushButton("APROVAR E EXECUTAR");self.approve.setObjectName("primary");self.approve.clicked.connect(self.execute);ll.addWidget(self.approve)
        right=QWidget();rl=QVBoxLayout(right);rl.setContentsMargins(10,0,0,0)
        rl.addWidget(QLabel("EXECUÇÃO E RESULTADOS LOCAIS"))
        self.log=QPlainTextEdit();self.log.setReadOnly(True);rl.addWidget(self.log)
        self.capture=QLabel("Captura disponível quando o plano usar take_screenshot");self.capture.setAlignment(Qt.AlignCenter);self.capture.setMinimumHeight(120);self.capture.setWordWrap(True);rl.addWidget(self.capture)
        split.addWidget(left);split.addWidget(right);main.addWidget(split,1)
        footer=QHBoxLayout();self.status=QLabel("Pronto • configure a Groq e escolha uma pasta");self.status.setWordWrap(True);footer.addWidget(self.status,1)
        self.elapsed=QLabel("00:00");footer.addWidget(self.elapsed)
        self.pause_button=QPushButton("Pausar");self.pause_button.clicked.connect(self.toggle_pause);footer.addWidget(self.pause_button)
        self.cancel_button=QPushButton("Cancelar");self.cancel_button.clicked.connect(self.cancel);footer.addWidget(self.cancel_button)
        main.addLayout(footer)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(1000)
        self.setStyleSheet("""
QMainWindow,QDialog {background:#0e1726;color:#e7eef8;}
QWidget {font-family:'Segoe UI';font-size:13px;color:#e7eef8;}
QLineEdit,QPlainTextEdit,QComboBox {background:#172438;border:1px solid #31425a;border-radius:7px;padding:9px;selection-background-color:#226b66;}
QPushButton {background:#23364d;border:1px solid #3a5068;border-radius:7px;padding:10px 14px;}
QPushButton:hover {background:#304961;} QPushButton:disabled {color:#718096;background:#192333;}
QPushButton#primary {background:#1e7568;border:1px solid #48b39c;font-weight:700;}
QLabel {background:transparent;} QComboBox QAbstractItemView {background:#172438;}
QMessageBox {background:#172438;}
""")
        self.busy(False)

    def busy(self,value):
        for w in [self.generate,self.approve,self.root,self.browse,self.mode,self.settings_button,self.load,self.save,self.command]:w.setEnabled(not value)
        self.plan.setReadOnly(value)
        self.pause_button.setEnabled(value);self.cancel_button.setEnabled(value)

    def choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,"Pasta autorizada")
        if folder: self.root.setText(folder)

    def settings(self):
        d=Settings(self,self.config)
        if d.exec()!=QDialog.Accepted:return
        try:
            if d.key.text():save_key(d.key.text())
            self.config.update(model=d.model.text().strip(),domains=d.domains.text().strip())
            self.persist()
        except Exception as e:QMessageBox.warning(self,"Configuração não salva",str(e))
        finally:d.key.clear()

    def persist(self):
        self.config["root"]=self.root.text()
        (self.data/"config.json").write_text(json.dumps(self.config,indent=2),encoding="utf-8")

    def policy(self):
        if not self.root.text().strip():raise ValueError("Selecione a pasta autorizada.")
        return Policy(self.root.text(),self.config.get("domains","").split(","))

    def launch(self,plan_text):
        try:
            policy=self.policy()
            key=get_key() if plan_text is None else ""
            if plan_text is None and not key:raise ValueError("Adicione sua chave Groq em Configurações. Obtenha-a em console.groq.com/keys.")
            if plan_text is not None:
                tools,_=registry(policy);Plan.parse(plan_text,tools)
            self.persist()
            self.worker=Worker(policy,self.config.get("model","openai/gpt-oss-120b"),self.command.toPlainText(),plan_text,self.mode.currentData(),self.audit,key)
            self.worker.event.connect(self.on_event);self.worker.approval.connect(self.confirm)
            self.worker.finished.connect(self.finished)
            self.started=time.monotonic();self.paused=False;self.pause_button.setText("Pausar")
            self.busy(True);self.status.setText("Planejando com Groq…" if plan_text is None else "Executando plano aprovado…")
            self.worker.start()
        except Exception as e:QMessageBox.warning(self,"Não foi possível iniciar",str(e))

    def create_plan(self):
        if not self.command.toPlainText().strip():return
        self.plan.clear();self.launch(None)

    def execute(self):
        try:
            tools,_=registry(self.policy());plan=Plan.parse(self.plan.toPlainText(),tools)
        except Exception as e:QMessageBox.warning(self,"Plano inválido",str(e));return
        red=sum(tools[s.tool].risk=="vermelho" for s in plan.steps)
        msg=QMessageBox(self);msg.setWindowTitle("Aprovar plano")
        msg.setText(f"Executar {len(plan.steps)} etapas em {self.root.text()}?\n{red} etapas exigirão confirmação específica.\nAlterações concluídas não têm desfazer automático.")
        msg.setDetailedText("\n".join(f"{i+1}. [{tools[s.tool].risk}] {s.description}\n{ s.tool } {json.dumps(s.args,ensure_ascii=False)}" for i,s in enumerate(plan.steps)))
        msg.setStandardButtons(QMessageBox.Yes|QMessageBox.No);msg.setDefaultButton(QMessageBox.No)
        if msg.exec()==QMessageBox.Yes:self.launch(plan.to_json())

    def confirm(self,details):
        if not self.worker or self.worker.stop.is_set():return
        box=QMessageBox(self);box.setWindowTitle("Autorização • " + details["risk"].upper())
        box.setText(details["description"] + "\n\nFerramenta: " + details["tool"])
        box.setInformativeText("Confira destino e dados. Para login/MFA/CAPTCHA, intervenha manualmente no navegador. Autorize somente após revisar.")
        box.setDetailedText(json.dumps(details["args"],ensure_ascii=False,indent=2,default=str))
        box.setStandardButtons(QMessageBox.Yes|QMessageBox.No);box.setDefaultButton(QMessageBox.No)
        decision=box.exec()==QMessageBox.Yes
        self.worker.decision=decision;self.worker.answer.set()

    def on_event(self,kind,data):
        if kind=="plan":self.plan.setPlainText(data);self.status.setText("Plano pronto para revisão. Nada foi executado.")
        elif kind=="status":self.status.setText(data);self.log.appendPlainText(data)
        elif kind=="step":
            text=f"→ {data['index']+1}. [{data['risk']}] {data['description']}"
            self.status.setText(text);self.log.appendPlainText(text)
        elif kind=="result":
            self.log.appendPlainText("✓ " + json.dumps(data,ensure_ascii=False,default=str)[:14000])
            result=data["result"]
            if isinstance(result,dict) and "screenshot" in result:
                self.capture.setPixmap(QPixmap(result["screenshot"]).scaled(470,200,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        elif kind=="error":
            self.status.setText("Interrompido • revise o plano e o resultado parcial")
            self.log.appendPlainText("ERRO: " + data)
            QMessageBox.warning(self,"Execução interrompida",data)

    def finished(self):
        self.busy(False)
        if self.worker and self.worker.stop.is_set():self.status.setText("Cancelado. Ações concluídas permanecem aplicadas.")
        self.started=0

    def toggle_pause(self):
        if not self.worker or not self.worker.executor:return
        self.paused=not self.paused
        if self.paused:self.worker.executor.pause()
        else:self.worker.executor.resume()
        self.pause_button.setText("Continuar" if self.paused else "Pausar")
        self.status.setText("Pausa solicitada; vale antes da próxima etapa." if self.paused else "Continuando…")

    def cancel(self):
        if self.worker:self.worker.cancel();self.status.setText("Cancelamento solicitado; aguardando a operação atual terminar.")

    def tick(self):
        if self.started:
            elapsed=int(time.monotonic()-self.started);self.elapsed.setText(f"{elapsed//60:02}:{elapsed%60:02}")

    def save_plan(self):
        try:
            tools,_=registry(self.policy());plan=Plan.parse(self.plan.toPlainText(),tools)
            name,ok=QInputDialog.getText(self,"Salvar automação","Nome da automação:")
            if not ok:return
            import re
            if not re.fullmatch(r"[\w -]{1,60}",name):raise ValueError("Use letras, números, espaços ou hífen.")
            with (self.library/(name+".json")).open("x",encoding="utf-8") as f:f.write(plan.to_json())
            self.status.setText("Automação salva: " + name)
        except Exception as e:QMessageBox.warning(self,"Não foi possível salvar",str(e))

    def load_plan(self):
        path,_=QFileDialog.getOpenFileName(self,"Minhas automações",str(self.library),"Planos JSON (*.json)")
        if not path:return
        try:
            tools,_=registry(self.policy());plan=Plan.parse(Path(path).read_text(encoding="utf-8"),tools)
            self.plan.setPlainText(plan.to_json());self.command.setPlainText("Automação carregada: " + plan.title)
            self.status.setText("Revise o plano carregado antes de aprovar.")
        except Exception as e:QMessageBox.warning(self,"Plano inválido",str(e))

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.cancel();event.ignore()
            self.status.setText("Aguardando término da operação atual. Feche novamente quando terminar.")
        else:event.accept()
