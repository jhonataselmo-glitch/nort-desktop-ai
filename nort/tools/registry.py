import inspect
from dataclasses import dataclass
from nort.tools.files import FileTools
from nort.tools.data import DataTools
from nort.tools.browser import BrowserTools
from nort.tools.windows import WindowsTools


@dataclass
class Tool:
    name: str
    risk: str
    handler: object
    agent: str

    def describe(self):
        return {"name":self.name, "args":str(inspect.signature(self.handler)), "description":self.handler.__doc__, "risk":self.risk, "agent":self.agent}


def human_checkpoint(message):
    """Pausa para usuário revisar dados, resolver login/MFA/CAPTCHA ou executar etapa manual. Não executa a tarefa descrita."""
    return {"manual_checkpoint_acknowledged":True}


def registry(policy):
    files,data,browser,windows=FileTools(policy),DataTools(policy),BrowserTools(policy),WindowsTools()
    result={}
    groups=[(files,"DATA AGENT",{"list_files":"verde","copy_file":"amarelo","move_file":"vermelho","assert_file":"verde"}),
            (data,"DATA AGENT",{"read_excel":"verde","filter_rows":"verde","validate_rows":"verde","write_excel":"amarelo","update_excel":"amarelo"}),
            (browser,"BROWSER AGENT",{"open_url":"vermelho","browser_read":"verde","browser_click":"vermelho","browser_fill":"vermelho","assert_text":"verde","take_screenshot":"amarelo"}),
            (windows,"WINDOWS AGENT",{"open_application":"vermelho","read_screen":"verde","windows_click":"vermelho"})]
    for owner,agent,names in groups:
        for name,risk in names.items(): result[name]=Tool(name,risk,getattr(owner,name),agent)
    result["human_checkpoint"]=Tool("human_checkpoint","vermelho",human_checkpoint,"SECURITY GUARD")
    return result,browser
