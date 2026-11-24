from __future__ import annotations
import copy
import json
import threading
import time
import uuid
from nort.core.models import Plan, resolve


class Cancelled(Exception): pass


class Executor:
    def __init__(self, registry, audit, approve, emit=lambda *args:None):
        self.registry,self.audit,self.approve,self.emit=registry,audit,approve,emit
        self.cancelled=threading.Event()
        self.running=threading.Event()
        self.running.set()

    def cancel(self): self.cancelled.set(); self.running.set()
    def pause(self): self.running.clear()
    def resume(self): self.running.set()

    def checkpoint(self):
        while not self.running.wait(0.1):
            if self.cancelled.is_set(): raise Cancelled()
        if self.cancelled.is_set(): raise Cancelled()

    def run(self, plan, mode="assistido", command=""):
        if mode not in {"assistido","automatico"}: raise ValueError("Modo inválido.")
        # Validate and snapshot again: edits cannot reuse an earlier authorization.
        plan=Plan.parse(plan.to_json(),self.registry)
        run_id=str(uuid.uuid4())
        results={}
        self.audit.record("run_started",run_id=run_id,command=command,plan=json.loads(plan.to_json()))
        try:
            for index,step in enumerate(plan.steps):
                self.checkpoint()
                tool=self.registry[step.tool]
                args=copy.deepcopy(resolve(step.args,results))
                if mode=="assistido" or tool.risk=="vermelho":
                    self.emit("status","Aguardando autorização: " + step.description)
                    decision=self.approve(step,tool,args)
                    self.audit.record("authorization",run_id=run_id,step=step.id,approved=bool(decision))
                    if not decision: raise Cancelled()
                self.checkpoint()
                self.audit.record("step_started",run_id=run_id,step=step.id,tool=tool.name,risk=tool.risk,args=args)
                self.emit("step",{"index":index,"description":step.description,"risk":tool.risk})
                started=time.monotonic()
                result=tool.handler(**args)
                results[step.id]=result
                # Data records stay local in execution memory; audit stores counts, paths and metadata.
                summary={"records":len(result)} if isinstance(result,list) else {"characters":len(result)} if isinstance(result,str) else result
                self.audit.record("step_completed",run_id=run_id,step=step.id,result=summary,seconds=round(time.monotonic()-started,3))
                self.emit("result",{"index":index,"result":result})
            self.checkpoint()
            self.audit.record("run_completed",run_id=run_id)
            self.emit("status","Plano concluído. Confira os resultados e as verificações registradas.")
            return results
        except Cancelled:
            self.audit.record("run_cancelled",run_id=run_id)
            self.emit("status","Cancelado. Ações já concluídas não foram desfeitas.")
            return results
        except Exception as e:
            self.audit.record("run_failed",run_id=run_id,error=type(e).__name__,message=str(e))
            self.emit("status","Interrompido: " + str(e) + " Revise a tela e o plano antes de executar novamente.")
            raise
