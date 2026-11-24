from __future__ import annotations
import inspect
import json
import re
from dataclasses import dataclass, asdict


@dataclass
class Step:
    id: str
    description: str
    tool: str
    args: dict


@dataclass
class Plan:
    title: str
    steps: list[Step]

    def to_json(self):
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def parse(cls, text, registry):
        if len(text) > 200_000:
            raise ValueError("Plano muito grande.")
        obj = json.loads(text)
        if not isinstance(obj, dict) or set(obj) != {"title", "steps"}:
            raise ValueError("Plano deve conter apenas title e steps.")
        if not isinstance(obj["title"], str) or not obj["title"].strip():
            raise ValueError("Título inválido.")
        if not isinstance(obj["steps"], list) or not 1 <= len(obj["steps"]) <= 40:
            raise ValueError("O plano precisa de 1 a 40 etapas.")
        seen, steps = set(), []
        def refs(value):
            if isinstance(value, dict):
                if "$ref" in value:
                    if set(value) != {"$ref"} or value["$ref"] not in seen:
                        raise ValueError("Referência inválida: use somente resultado de etapa anterior.")
                else:
                    for v in value.values(): refs(v)
            elif isinstance(value, list):
                for v in value: refs(v)
        for raw in obj["steps"]:
            if not isinstance(raw, dict) or set(raw) != {"id", "description", "tool", "args"}:
                raise ValueError("Etapa inválida.")
            step = Step(**raw)
            if not isinstance(step.id, str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]{0,39}", step.id) or step.id in seen:
                raise ValueError("ID de etapa inválido ou repetido.")
            if not isinstance(step.description, str) or not step.description.strip():
                raise ValueError("Descrição obrigatória.")
            if not isinstance(step.tool, str) or step.tool not in registry:
                raise ValueError("Ferramenta não permitida.")
            if not isinstance(step.args, dict):
                raise ValueError("Argumentos devem ser um objeto.")
            inspect.signature(registry[step.tool].handler).bind(**step.args)
            refs(step.args)
            seen.add(step.id)
            steps.append(step)
        return cls(obj["title"], steps)


def resolve(value, results):
    if isinstance(value, dict):
        if set(value) == {"$ref"}: return results[value["$ref"]]
        return {k: resolve(v, results) for k, v in value.items()}
    if isinstance(value, list): return [resolve(v, results) for v in value]
    return value
