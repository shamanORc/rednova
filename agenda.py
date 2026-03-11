"""Agenda e contratos do RedNova"""
import json, os
from datetime import datetime

ARQUIVO = "agenda.json"

def carregar():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO) as f:
            return json.load(f)
    return {"contratos": []}

def salvar(data):
    with open(ARQUIVO, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def listar():
    data = carregar()
    contratos = data.get("contratos", [])
    if not contratos:
        return "📋 *Agenda vazia*\n\nNenhum contrato cadastrado.\n\nUse:\n`/contrato NomeCliente | alvo.com | 15/03/2026 | R$5000`"
    out = ["📋 *CONTRATOS ATIVOS — REDNOVA*\n"]
    for i, c in enumerate(contratos, 1):
        status = "✅" if c.get("concluido") else "⏳"
        out.append(f"{status} *{i}. {c['cliente']}*")
        out.append(f"   🎯 Alvo: `{c.get('alvo','?')}`")
        out.append(f"   📅 Prazo: {c.get('prazo','?')}")
        out.append(f"   💰 Valor: {c.get('valor','?')}")
        if c.get("obs"):
            out.append(f"   📝 {c['obs']}")
        out.append("")
    return "\n".join(out)

def adicionar(texto):
    """Formato: Cliente | alvo.com | 15/03/2026 | R$5000"""
    partes = [p.strip() for p in texto.split("|")]
    if len(partes) < 2:
        return "❌ Formato: `NomeCliente | alvo.com | prazo | valor`"
    data = carregar()
    contrato = {
        "cliente":   partes[0],
        "alvo":      partes[1] if len(partes) > 1 else "",
        "prazo":     partes[2] if len(partes) > 2 else "",
        "valor":     partes[3] if len(partes) > 3 else "",
        "obs":       partes[4] if len(partes) > 4 else "",
        "concluido": False,
        "criado":    datetime.now().strftime("%d/%m/%Y"),
    }
    data["contratos"].append(contrato)
    salvar(data)
    return f"✅ Contrato adicionado!\n\n*Cliente:* {contrato['cliente']}\n*Alvo:* {contrato['alvo']}\n*Prazo:* {contrato['prazo']}\n*Valor:* {contrato['valor']}"

def concluir(numero):
    data = carregar()
    contratos = data.get("contratos", [])
    idx = int(numero) - 1
    if 0 <= idx < len(contratos):
        contratos[idx]["concluido"] = True
        salvar(data)
        return f"✅ Contrato *{contratos[idx]['cliente']}* marcado como concluído!"
    return "❌ Número inválido."

def remover(numero):
    data = carregar()
    contratos = data.get("contratos", [])
    idx = int(numero) - 1
    if 0 <= idx < len(contratos):
        nome = contratos[idx]["cliente"]
        contratos.pop(idx)
        salvar(data)
        return f"🗑️ Contrato *{nome}* removido."
    return "❌ Número inválido."
