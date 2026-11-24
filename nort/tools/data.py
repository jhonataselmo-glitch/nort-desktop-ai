from datetime import date, datetime
import re


def literal(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    if isinstance(value, (dict, list)): raise ValueError("Célula deve conter um valor simples.")
    return value


class DataTools:
    def __init__(self, policy): self.policy = policy

    def read_excel(self, path, sheet=None):
        """Lê XLSX: primeira linha contém cabeçalhos únicos; máximo 10000 linhas e 100 colunas."""
        from openpyxl import load_workbook
        p = self.policy.path(path)
        if p.suffix.lower() != ".xlsx" or p.stat().st_size > 20_000_000: raise ValueError("Use XLSX até 20 MB.")
        wb = load_workbook(p, read_only=True, data_only=True, keep_links=False)
        try:
            ws = wb[sheet] if sheet else wb.active
            if ws.max_row > 10001 or ws.max_column > 100: raise ValueError("Planilha excede os limites do MVP.")
            rows = iter(ws.iter_rows(values_only=True))
            headers = [str(x).strip() if x is not None else "" for x in next(rows, [])]
            if not headers or not all(headers) or len(set(headers)) != len(headers): raise ValueError("Cabeçalhos ausentes ou repetidos.")
            return [{k: (v.isoformat() if isinstance(v, (date, datetime)) else v) for k,v in zip(headers,row)} for row in rows if any(v is not None for v in row)]
        finally: wb.close()

    def filter_rows(self, rows, column, operator, value):
        """Filtra lista de objetos. Operadores: equals, not_equals, contains, month (YYYY-MM)."""
        if not isinstance(rows, list) or len(rows) > 10000: raise ValueError("Dados inválidos.")
        if operator not in {"equals","not_equals","contains","month"}: raise ValueError("Operador inválido.")
        if operator == "month" and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", str(value)): raise ValueError("Mês deve ser YYYY-MM.")
        result=[]
        for row in rows:
            if column not in row: raise ValueError("Coluna não encontrada: " + column)
            x=row[column]
            ok = (x == value if operator == "equals" else x != value if operator == "not_equals" else str(value) in str(x) if operator == "contains" else str(x)[:7] == value)
            if ok: result.append(row)
        return result

    def validate_rows(self, rows, required_columns):
        """Interrompe se algum registro não contiver todos os campos obrigatórios; devolve registros."""
        for i,row in enumerate(rows, 2):
            for col in required_columns:
                if row.get(col) is None or str(row.get(col)).strip() == "": raise ValueError("Campo obrigatório ausente na linha %d: %s" % (i,col))
        return rows

    def write_excel(self, path, rows):
        """Cria NOVO XLSX a partir de lista de objetos. Nunca sobrescreve. Neutraliza fórmulas."""
        from openpyxl import Workbook, load_workbook
        p=self.policy.path(path)
        if p.suffix.lower() != ".xlsx": raise ValueError("Destino deve ser XLSX.")
        if not isinstance(rows,list) or not rows or len(rows)>10000: raise ValueError("Forneça de 1 a 10000 registros.")
        headers=list(rows[0])
        if not headers or len(headers)>100 or any(set(row)!=set(headers) for row in rows): raise ValueError("Colunas inconsistentes.")
        wb=Workbook()
        ws=wb.active
        ws.title="Dados"
        ws.append([literal(h) for h in headers])
        for row in rows: ws.append([literal(row[h]) for h in headers])
        ws.freeze_panes="A2"
        ws.auto_filter.ref=ws.dimensions
        for cells in ws.columns: ws.column_dimensions[cells[0].column_letter].width=24
        # Exclusive creation prevents accidental overwrite even when destination appears concurrently.
        try:
            with p.open("xb") as stream: wb.save(stream)
        except FileExistsError: raise ValueError("Destino já existe; escolha outro nome.") from None
        finally: wb.close()
        check=load_workbook(p, read_only=True)
        try:
            if check.active.max_row != len(rows)+1: raise RuntimeError("Falha na validação do XLSX gravado.")
        finally: check.close()
        return {"path":str(p), "rows":len(rows), "verified":True}

    def update_excel(self, source, destination, cells, sheet=None):
        """Altera células {A2: valor} em uma CÓPIA XLSX. Mantém o original. Sem macros."""
        from openpyxl import load_workbook
        src,dst=self.policy.path(source),self.policy.path(destination)
        if src.suffix.lower() != ".xlsx" or dst.suffix.lower() != ".xlsx": raise ValueError("Use XLSX.")
        if src.stat().st_size > 20_000_000 or not isinstance(cells,dict) or len(cells)>1000: raise ValueError("Limite excedido.")
        wb=load_workbook(src, keep_links=False)
        try:
            ws=wb[sheet] if sheet else wb.active
            for address,value in cells.items():
                if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]{0,5}",address): raise ValueError("Endereço inválido.")
                ws[address]=literal(value)
            with dst.open("xb") as stream: wb.save(stream)
        finally: wb.close()
        return {"path":str(dst), "cells_changed":len(cells)}
