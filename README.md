# fminside-scraper — FMInside → Gofoot

Ferramenta local para extrair jogadores do [fminside.net](https://fminside.net) e gerar JSON no formato do **Gofoot Studio**.

## O que você precisa ter instalado

Esta ferramenta **não é um programa .exe pronto**. Ela roda com **Python**.

1. Instale o **Python 3.11 ou superior** (recomendado 3.12+):  
   https://www.python.org/downloads/
2. Na instalação no Windows, marque a opção **"Add python.exe to PATH"** (adicionar ao PATH).
3. Abra o terminal (PowerShell ou Prompt de Comando) e confira:

```bash
python --version
```

Se aparecer algo como `Python 3.12.x`, está ok.  
Se der erro de comando não encontrado, o Python não está no PATH — reinstale marcando essa opção, ou use `py --version`.

Também é necessário **conexão com a internet** (o scraping acessa o fminside.net).

## Instalação das dependências (só na primeira vez)

No terminal, entre na pasta do projeto e rode:

```bash
cd d:\dev\jogos\fminside-scraper
python -m pip install -r requirements.txt
```

## App web local

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8765
```

Depois abra no navegador: http://127.0.0.1:8765

Na tela você escolhe **Clube** ou **Liga**, inicia o scraping e baixa os JSON gerados.

Para ligas com nome repetido (ex.: **Série A** no Brasil e **Serie A** na Itália), preencha também **Nação** (país da competição, ex.: `Brazil` + `Série A`). O site mistura esses nomes no filtro de jogadores; a ferramenta lista os clubes e usa o título real da liga (`Brasileiro Série A` vs `Serie A`) para separar.

Para parar o servidor: no terminal, `Ctrl + C`.

## CLI (linha de comando)

```bash
python -m fminside.cli --club "Real Madrid"
python -m fminside.cli --league "Premier League" --nation "England"
python -m fminside.cli --league "Série A" --nation "Brazil"
python -m fminside.cli --club "FC Bayern" --max-players 30 --max-pages 2
```

Use os **nomes exatos** como aparecem no fminside (em inglês: `Brazil`, `Italy`, `England`…).

## Onde ficam os arquivos

- Clube → `output/clubs/{nome_do_clube}.json`
- Liga → `output/leagues/{liga}/{clube}.json`
- Liga + nação → `output/leagues/{nacao}/{liga}/{clube}.json`

Esses JSON podem ser importados no Gofoot Studio (aba de atualizar CSV / importar equipas).

## Problemas comuns

| Situação | O que fazer |
|----------|-------------|
| `python` não é reconhecido | Reinstale o Python marcando **Add to PATH** |
| `pip` / módulos não encontrados | Rode `python -m pip install -r requirements.txt` de novo |
| Porta 8765 em uso | Troque a porta: `--port 8766` e abra `http://127.0.0.1:8766` |
| Scraping muito lento | Normal — há delay entre requests para não sobrecarregar o site |
